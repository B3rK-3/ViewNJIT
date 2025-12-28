from constants import (
    CourseQueryFormat,
    RPCRequest,
    graph_data,
    COLLECTION_NAME,
    CourseMetadata,
    GEMINI_API_KEY,
    UserFulfilled,
    CHAT_N,
    AddUserPrereqsFormat,
    CHROMA_KEY,
    CHROMA_TENANT,
    CHROMA_DB,
)
import hashlib
import chromadb
from typing import List, Tuple, Dict, Any, Optional
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder
import time
from google import genai
from google.genai import types
import json

user_prereqs: UserFulfilled = UserFulfilled(courses={})
# use cuda
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2",
    device="cuda",
)

# global cross encoder
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cuda")

# global chromadb client
chroma_client = chromadb.CloudClient(
    api_key=CHROMA_KEY,
    tenant=CHROMA_TENANT,
    database=CHROMA_DB,
)

# global chromadb collection
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME, embedding_function=ef
)


def FunctionResult(method: str, response: Any, message_to_ai: str):
    return {
        "method": method,
        "response": response,
        "message_to_ai": message_to_ai,
    }


def generate_hash(title: str, description: str) -> Tuple[str, str]:
    """
    generates an md5 hash of the given text.
    returns (hash, combined_text).
    """
    # handle none
    t = title if title else ""
    d = description if description else ""

    combined_text = f"{t} {d}".strip()
    return (hashlib.md5(combined_text.encode("utf-8")).hexdigest(), combined_text)


def initialize_database() -> None:
    """
    initializes chromadb and populates it with course data.
    """
    print("Initializing ChromaClient...")

    try:
        heartbeat = chroma_client.heartbeat()
        print("ChromaDB Heartbeat:", heartbeat)
    except Exception as e:
        print("Could not initialize ChromaDB PersistentClient at ./chromadb")
        raise e

    print(f"Getting or creating collection '{COLLECTION_NAME}'...")

    ids_to_upsert: List[str] = []
    documents_to_upsert: List[str] = []
    metadatas_to_upsert: List[CourseMetadata] = []

    print("Checking for updates in graph data...")

    for course_id, info in graph_data.items():
        title = info.title
        description = info.desc

        computed_hash, combined_text = generate_hash(title, description)

        # retrieve specific item to check hash
        result = collection.get(ids=[course_id], include=["metadatas"])

        needs_upsert = False
        if not result["ids"]:
            needs_upsert = True
        else:
            existing_metas = result.get("metadatas")
            existing_meta = existing_metas[0] if existing_metas else None

            if not existing_meta or existing_meta.get("hash") != computed_hash:
                print(f"Course {course_id} changed, re-indexing...")
                needs_upsert = True

        if needs_upsert:
            ids_to_upsert.append(course_id)
            documents_to_upsert.append(combined_text)
            metadata: CourseMetadata = {
                "title": title,
                "description": description,
                "hash": computed_hash,
            }
            metadatas_to_upsert.append(metadata)

        # batch upsert
        if len(ids_to_upsert) >= 100:
            collection.upsert(
                ids=ids_to_upsert,
                documents=documents_to_upsert,
                metadatas=metadatas_to_upsert,  # type: ignore
            )
            print(f"Upserted {len(ids_to_upsert)} courses...")
            ids_to_upsert = []
            documents_to_upsert = []
            metadatas_to_upsert = []

    # final batch
    if len(ids_to_upsert) > 0:
        collection.upsert(
            ids=ids_to_upsert,
            documents=documents_to_upsert,
            metadatas=metadatas_to_upsert,  # type: ignore
        )
        print(f"Final update for {len(ids_to_upsert)} courses complete.")

    print("Database synchronization complete.")


def course_query(args: CourseQueryFormat) -> List[Dict[str, Any]]:
    """
    queries the course database for semantic similarities.
    Re-rank the provided list of courses based on relevance to the query.

    IMPORTANT RULES:
    - You MUST return ALL provided courses.
    - You MUST NOT remove, filter, or omit any course.
    - You MUST NOT add new courses.
    - You MUST only reorder the existing list.
    - If uncertain, preserve the original order.

    Returns:
        Top_n matching courses based on query and only_prereqs_fulfilled.
    """
    print("DEBUG:", args.model_dump())
    query_text = args.query
    n = args.top_n

    try:
        if args.only_prereqs_fulfilled:
            results = collection.query(
                ids=get_available_courses(), query_texts=[query_text], n_results=n
            )
        else:
            results = collection.query(query_texts=[query_text], n_results=n)

        if not results["ids"]:
            return []

        flat_results: List[Dict[str, Any]] = []
        ids_list = results["ids"][0]
        distances_list = (
            results["distances"][0] if results["distances"] else [None] * len(ids_list)
        )
        metadatas_list = (
            results["metadatas"][0] if results["metadatas"] else [None] * len(ids_list)
        )
        documents_list = (
            results["documents"][0] if results["documents"] else [None] * len(ids_list)
        )

        for i, cid in enumerate(ids_list):
            flat_results.append(
                {
                    "id": cid,
                    "document": documents_list[i],
                    "init_distance": distances_list[i],
                }
            )

        # rerank with cross encoder
        if flat_results:
            pairs = [[query_text, item["document"]] for item in flat_results]
            scores = cross_encoder.predict(pairs)
            for i, item in enumerate(flat_results):
                item["score"] = float(scores[i])

            # sort by score descending
            flat_results.sort(key=lambda x: x["score"], reverse=True)
        print("DEBUG:", len(flat_results), "courses returned")
        return flat_results

    except Exception as e:
        print("Error querying ChromaDB:", e)
        return []


def update_user_prereqs(args: AddUserPrereqsFormat):
    """
    Adds or updates the user courses for later filtering.

    Returns:
        All use fullfilments after current update
    """
    print("DEBUG:", args.model_dump())
    for course in args.courses:
        user_prereqs.courses[course.name] = course
    return user_prereqs.model_dump()


def is_grade_sufficient(user_grade: str, min_grade: Optional[str]) -> bool:
    """
    Checks if user_grade >= min_grade based on fixed set of grades.
    """
    grade_values = {"A": 4.0, "B+": 3.5, "B": 3.0, "C+": 2.5, "C": 2.0, "F": 0.0}

    # If user grade unknown, assume fail/invalid
    val_user = grade_values.get(user_grade, 0.0)

    # If no min_grade specified, assume 'C' (passing) is required
    # (Or just that any non-F grade is sufficient, but F=0 so C>=F check works if min=C)
    if not min_grade:
        return val_user >= 2.0

    val_min = grade_values.get(
        min_grade, 2.0
    )  # Default to C if min_grade str is unknown
    return val_user >= val_min


def check_prereq_tree(node: Any) -> bool:
    """
    Recursively checks if a prereq tree node is satisfied by user_prereqs.
    Only considers CourseNodeModel; returns False for other types for now.
    """
    if node is None:
        return True

    # Because of Pydantic union, access attributes directly.
    # Check type by attribute 'type' (discriminator)
    if not hasattr(node, "type"):
        return False

    node_type = node.type

    if node_type == "AND":
        # All children must be satisfied
        if not node.children:
            return True
        return all(check_prereq_tree(child) for child in node.children)

    elif node_type == "OR":
        # At least one child satisfied
        if not node.children:
            return True  # Empty OR? Usually implies nothing needed? Or failure? Assume True if empty list (trivial)
        return any(check_prereq_tree(child) for child in node.children)

    elif node_type == "COURSE":
        # Check against global user_prereqs
        c_name = node.course
        if c_name in user_prereqs.courses:
            u_info = user_prereqs.courses[c_name]
            return is_grade_sufficient(u_info.grade, node.min_grade)
        return False

    # Other types (PLACEMENT, PERMISSION, etc.) ignored as per instruction
    return False


def get_available_courses() -> List[str]:
    """
    Returns all course_names from graph_data where prereq_tree is satisfied.
    """
    satisfied_courses = []

    for course_id, info in graph_data.items():
        if course_id in user_prereqs.courses.keys():
            continue
        if check_prereq_tree(info.prereq_tree):
            satisfied_courses.append(course_id)

    return satisfied_courses


def gemini_call():
    client = genai.Client()
    config = types.GenerateContentConfig(tools=[update_user_prereqs, course_query])
    history: List[types.Content] = []

    # We'll use a loop to handle the initial inquiry and subsequent turns
    first_input = input("User: ").strip()
    current_input = first_input

    while current_input:
        # Include current data status in each user message to keep AI informed
        payload = {
            "user_prereqs": user_prereqs.model_dump(),
        }
        prompt = f"{current_input}\n\nUSER_DATA_JSON:\n{json.dumps(payload)}"

        # Add to history
        history.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        # Limit history to past CHAT_N messages
        if len(history) > CHAT_N:
            history = history[-CHAT_N:]

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=config,
        )

        if response.text:
            print(f"Assistant: {response.text}")
            # Add model response to history
            history.append(response.candidates[0].content)
        print()

        current_input = input("User: ").strip()
        if not current_input:
            break


"""
Handler = Callable[[BaseModel, str, str], Any]
REGISTRY: Dict[str, tuple[Type[BaseModel], Handler, str]] = {
    "course_query": (
        CourseQueryFormat,
        course_query,
        "You should always choose the best ones and return in the format of course_id: document.",
    ),
    "add_user_prereqs": (
        AddUserPrereqsFormat,
        update_user_prereqs,
        "Added user prereqs.",
    ),
}


def handle_request(raw: Dict[str, Any]) -> Any:
    call_signature = RPCRequest.model_validate(raw)

    entry = REGISTRY.get(call_signature.method)
    if entry is None:
        return {
            "ok": False,
            "error": {
                "code": "METHOD_NOT_FOUND",
                "message": f"Unknown method: {call_signature.method}",
                "allowed_methods": sorted(REGISTRY.keys()),
            },
        }

    params_model, fn, message_to_ai = entry

    # Validate ONLY against the selected method's schema
    try:
        args = params_model.model_validate(call_signature.params)
    except ValidationError as e:
        return {
            "ok": False,
            "error": {
                "code": "INVALID_PARAMS",
                "message": "Params failed validation",
                "details": e.errors(),  # machine-readable
                "call_signature": call_signature.model_dump(),
            },
        }

    # Call handler
    return fn(args, call_signature.method, message_to_ai)


def manual_gemini_call():
    client = genai.Client()
    tools = types.Tool(
        function_declarations=[CourseQueryJSONformat, AddUserPrereqsJSONformat]
    )
    config = types.GenerateContentConfig(tools=[update_user_prereqs])
    run = True
    initial_message = "User inquiry: -Add CS 100 to my prereqs.-"
    messages = []

    while run:
        # Send request with function declarations
        data = {
            "User Prereqs Fulfilled": list(user_prereqs),
        }
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=initial_message
            + "\n These are the user data:\n"
            + json.dumps(data)
            + (
                (
                    "\n\n### TOOL_RESULT (do not ignore)\nTOOL_RESULT_JSON:\n"
                    + messages[-1]
                )
                if messages
                else ""
            ),
            config=config,
        )

        if response.candidates[0].content.parts[0].function_call:
            run = True
            function_call = response.candidates[0].content.parts[0].function_call
            print("Call Signature:", function_call)
            result = handle_request(
                {"method": function_call.name, "params": function_call.args}
            )
            print("Call Result:", result)
            print()
            messages.append(json.dumps(result))
        else:
            run = False
            print(response.text)
        print(user_prereqs)
"""
