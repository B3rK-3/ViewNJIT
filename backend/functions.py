from constants import CourseSearchFormat
from constants import VALID_COURSES
from constants import STANDINGS
from constants import current_session_prereqs
from constants import current_session_id
from constants import REDIS
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


# use cuda
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2", device="cpu"
)

# global cross encoder
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cuda")

# global chromadb client
chroma_client = chromadb.PersistentClient(path="./chromadb")

# global chromadb collection
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME, embedding_function=ef
)


def lcs_length(a: str, b: str) -> int:
    """Compute length of longest common subsequence (order preserved)."""
    a = a.replace(" ", "").lower()
    b = b.replace(" ", "").lower()

    dp = [0] * (len(b) + 1)

    for char_a in a:
        prev = 0
        for j, char_b in enumerate(b, 1):
            temp = dp[j]
            if char_a == char_b:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev = temp
    return dp[-1]


def best_course_matches(query: str) -> List[str]:
    scores = []
    max_score = 0

    for s in VALID_COURSES:
        score = lcs_length(query, s)
        scores.append((s, score))
        max_score = max(max_score, score)

    return [s for s, score in scores if score == max_score]


def is_valid_course(course_name: str) -> None | List[str]:
    valid_course = course_name in VALID_COURSES
    if valid_course:
        return None
    else:
        return best_course_matches(course_name)


def normalize_course(course_name: str) -> str | dict:
    """
    Validates and normalizes course names (e.g., CS101 -> CS 101).
    Returns the valid/fixed course name, or a dictionary with an error message and suggestions.
    """
    course_name = course_name.upper()
    similar_courses = is_valid_course(course_name)

    if not similar_courses:
        return course_name

    # Check for match ignoring spaces (e.g. "CS101" matches "CS 101")
    if len(similar_courses) == 1 and course_name.replace(" ", "") == similar_courses[
        0
    ].replace(" ", ""):
        return similar_courses[0]

    return {
        "error_message": f"{course_name} is not a valid course!",
        "did_you_mean": similar_courses[:5],
    }


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

    # Fetch significantly more candidates for the cross-encoder to re-rank
    # This ensures we don't miss relevant items that have lower vector scores
    fetch_k = 3000

    try:
        if args.only_prereqs_fulfilled:
            results = collection.query(
                ids=get_available_courses(), query_texts=[query_text], n_results=fetch_k
            )
        else:
            results = collection.query(query_texts=[query_text], n_results=fetch_k)

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
        print(
            "DEBUG:",
            [
                (each["id"], each["score"], each["init_distance"])
                for each in flat_results
            ],
        )

        # Return only the top N requested results
        return flat_results[:n]

    except Exception as e:
        print("Error querying ChromaDB:", e)
        return []


def update_user_prereqs(args: AddUserPrereqsFormat):
    """
    Adds or updates the user courses for later filtering.

    Args:
        ["courses": {"name": "course name", "grade": ""Grade recieved in course. A pass is a 'C'. Example: 'I passed a class', then grade = 'C'."},
        "equivalents": "List of courses that the user has equivalents for. Example: (equivalents for CS 350).",
        "standing": "User's academic standing (FRESHMAN, SOPHOMORE, JUNIOR, SENIOR, GRAD).",
        "semesters_left": "Number of semesters remaining until graduation."]

    Returns:
        All use fullfilments after current update
    """
    user_prereqs = current_session_prereqs.get()
    print("DEBUG:", args.model_dump())
    for course in args.courses:
        res = normalize_course(course.name)
        if isinstance(res, dict):
            return res
        course.name = res
        user_prereqs.courses[course.name] = course

    for eq in args.equivalents:
        res = normalize_course(eq)
        if isinstance(res, dict):
            return res
        user_prereqs.equivalents.append(res)

    if args.standing:
        user_prereqs.standing = args.standing
    if args.semesters_left:
        user_prereqs.semesters_left = args.semesters_left

    current_session_prereqs.set(user_prereqs)

    return user_prereqs.model_dump()


def get_course_description(args: CourseSearchFormat) -> str:
    """
    Get course description by course name.

    Args:
        {"course_name": "Name of the course to search for."}

    Returns:
        description of the course
    """
    print("DEBUG:", args.model_dump())
    res = normalize_course(args.course_name)
    if isinstance(res, dict):
        return res
    course_name = res

    return graph_data[course_name].desc


def can_take_course(args: CourseSearchFormat) -> bool | str:
    """
       Check if user can take a course.

    Args:
        {"course_name": "Name of the course to search for."}

    Returns:
        True or explanation of why user can't take it
    """
    print("DEBUG:", args.model_dump())
    res = normalize_course(args.course_name)
    if isinstance(res, dict):
        return res
    course_name = res

    user_prereqs = current_session_prereqs.get()

    if course_name in user_prereqs.courses:
        return f"You have already completed or are currently taking {course_name}."

    course_info = graph_data[course_name]
    return check_prereq_tree(course_info.prereq_tree, user_prereqs)


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


def check_prereq_tree(node: Any, user_prereqs: UserFulfilled) -> bool | str:
    """
    Recursively checks if a prereq tree node is satisfied by user_prereqs.
    Returns True if satisfied, or a string description of the missing requirements.
    """
    if node is None:
        return True

    if not hasattr(node, "type"):
        return "Internal error: Malformed prerequisite node."

    node_type = node.type

    if node_type == "AND":
        errors = []
        for child in node.children:
            res = check_prereq_tree(child, user_prereqs)
            if res is not True:
                errors.append(res)
        if not errors:
            return True
        if len(errors) == 1:
            return errors[0]
        return "All of the following must be met: (" + "; ".join(errors) + ")"

    elif node_type == "OR":
        errors = []
        for child in node.children:
            res = check_prereq_tree(child, user_prereqs)
            if res is True:
                return True
            errors.append(res)
        if not node.children:
            return True
        return "At least one of these must be met: (" + " OR ".join(errors) + ")"

    elif node_type == "COURSE":
        c_name = node.course
        if c_name not in user_prereqs.courses:
            return f"Missing course {c_name}"

        u_info = user_prereqs.courses[c_name]
        if node.min_grade and not is_grade_sufficient(u_info.grade, node.min_grade):
            needed = node.min_grade or "C"
            return f"User has {u_info.grade} in {c_name} suggests {u_info.grade}, but {needed} or better is required."
        return True

    elif node_type == "EQUIVALENT":
        missing = [c for c in node.courses if c not in user_prereqs.equivalents]
        if not missing:
            return True
        return f"Missing equivalent(s) for: {', '.join(missing)}"

    elif node_type == "STANDING":
        if not user_prereqs.standing:
            return f"Required academic standing: {node.normalized}"

        user_standing = user_prereqs.standing
        required_standing = node.normalized

        try:
            user_index = STANDINGS.index(user_standing)
            req_index = STANDINGS.index(required_standing)
        except ValueError:
            return f"Internal error: Invalid standing '{user_standing}' or '{required_standing}'."

        if user_index < req_index:
            return f"Standing is {user_standing}, but {required_standing} or higher is required."

        # Optional: check semesters_left if provided in node and user_prereqs
        if node.semesters_left is not None:
            if user_prereqs.semesters_left is None:
                return (
                    f"Missing 'semesters left' info (required: {node.semesters_left})"
                )
            if user_prereqs.semesters_left > node.semesters_left:
                return f"Requires {node.semesters_left} or fewer semesters left, but you have {user_prereqs.semesters_left}."

        return True

    # PLACEMENT, PERMISSION or unknown
    name = getattr(node, "name", getattr(node, "raw", node_type))
    return f"Special requirement needed: {node_type} ({name})"


def get_available_courses() -> List[str]:
    """
    Returns all course_names from graph_data where prereq_tree is satisfied.
    """
    satisfied_courses = []
    user_prereqs = current_session_prereqs.get()

    for course_id, info in graph_data.items():
        if course_id in user_prereqs.courses.keys():
            continue
        if check_prereq_tree(info.prereq_tree, user_prereqs) is True:
            satisfied_courses.append(course_id)
    print(satisfied_courses)
    return satisfied_courses


def dump_history(history):
    clean_history = []

    for h in history:
        # Convert the Content object to a dictionary
        data = h.model_dump(exclude_none=True)

        # Iterate through parts to remove 'thought' and 'thought_signature'
        if "parts" in data:
            for part in data["parts"]:
                # safely remove these keys if they exist
                part.pop("thought", None)
                part.pop("thought_signature", None)

        clean_history.append(data)

    return json.dumps(clean_history)


def load_history(history_str: str) -> List[types.Content]:
    """
    Loads a JSON string back into a list of Gemini Content objects.
    """
    if not history_str:
        return []
    try:
        data = json.loads(history_str)
        return [types.Content.model_validate(h) for h in data]
    except Exception as e:
        print(f"Error loading history: {e}")
        return []


def dump_prereqs(prereqs: UserFulfilled) -> str:
    """
    Converts a UserFulfilled object to a JSON string.
    """
    return prereqs.model_dump_json()


def load_prereqs(prereqs_str: str) -> UserFulfilled:
    """
    Loads a JSON string back into a UserFulfilled object.
    """
    if not prereqs_str:
        return UserFulfilled()
    try:
        return UserFulfilled.model_validate_json(prereqs_str)
    except Exception as e:
        print(f"Error loading prereqs: {e}")
        return UserFulfilled(courses={})


def gemini_call(input_text: str):
    client = genai.Client()

    session_id = current_session_id.get()
    history_raw = REDIS.get(f"{session_id}:history")
    prereqs_raw = REDIS.get(f"{session_id}:prereqs")
    history = load_history(history_raw)
    current_session_prereqs.set(load_prereqs(prereqs_raw))
    print(prereqs_raw)
    # print(history)

    sys_instruction = f"""User's current profile: {prereqs_raw}. Use tools to update courses, but you can remember other context from the conversation. 
    
    ONLY FOR CALLING update_user_prereqs LOOK AT THESE:
        If user tries to add a placement exam or permission:
            remind that those features are not implemented yet and its best to manually check
        If user tries to add equivalents:
            remind that they should confirm with registrar

    ONLY AFTER CALLING update_user_prereqs LOOK AT THESE:
        If user does not have standing or semesters left in profile:
            remind that adding those could provide more accurate search
    """

    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            tools=[
                update_user_prereqs,
                course_query,
                get_course_description,
                can_take_course,
            ],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False
            ),
        ),
        history=history,
    )

    response = chat.send_message(input_text)

    if response.text:
        print(f"Assistant: {response.text}")

    print(chat._curated_history)
    REDIS.set(f"{session_id}:history", dump_history(chat._curated_history))
    REDIS.set(f"{session_id}:prereqs", dump_prereqs(current_session_prereqs.get()))
    return response.text


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
