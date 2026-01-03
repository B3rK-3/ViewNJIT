from backend.constants import CHATBOT_PROMPT_FILE
from backend.constants import term_courses
from backend.constants import TERMS
from backend.constants import (
    CourseQueryFormat,
    RPCRequest,
    course_data,
    COLLECTION_NAME,
    CourseMetadata,
    GEMINI_API_KEY,
    UserFulfilled,
    CHAT_N,
    UpdateUserProfile,
    CHROMA_KEY,
    CHROMA_TENANT,
    CHROMA_DB,
    REDIS,
    STANDINGS,
    VALID_COURSES,
    CourseSearchFormat,
    MakeScheduleFormat,
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
from torch.cuda import is_available
import itertools


device = "cpu"
if is_available:
    device = "cuda"
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2", device=device
)

cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device=device)

chroma_client = chromadb.PersistentClient(path="./chromadb")

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

    for course_id, info in course_data.items():
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
                metadatas=metadatas_to_upsert,
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

        if node.semesters_left is not None:
            if user_prereqs.semesters_left is None:
                return (
                    f"Missing 'semesters left' info (required: {node.semesters_left})"
                )
            if user_prereqs.semesters_left > node.semesters_left:
                return f"Requires {node.semesters_left} or fewer semesters left, but you have {user_prereqs.semesters_left}."

        return True

    name = getattr(node, "name", getattr(node, "raw", node_type))
    return f"Special requirement needed: {node_type} ({name})"


def get_available_courses(
    user_prereqs: UserFulfilled,
    only_prereqs_fulfilled: bool,
    only_current_term: bool,
    term: str,
) -> List[str]:
    """
    Returns all course_names from course_data where prereq_tree is satisfied.
    """
    if only_current_term:
        course_names = term_courses[term]
    else:
        course_names = list(course_data.keys())

    if only_prereqs_fulfilled:
        satisfied_courses = []

        for course_name in course_names:
            if course_name in user_prereqs.courses.keys():
                continue

            if (
                check_prereq_tree(course_data[course_name].prereq_tree, user_prereqs)
                is True
            ):
                satisfied_courses.append(course_name)
        return satisfied_courses
    else:
        return course_names


def parse_time_str(time_str: str) -> Tuple[int, int]:
    """Parse time string like '11:30 AM - 12:50 PM' into (start_minutes, end_minutes)."""
    try:
        parts = time_str.strip().split(" - ")
        if len(parts) != 2:
            return None

        start_str, end_str = parts

        def time_to_minutes(t: str) -> int:
            t = t.strip()
            time_part, period = t.rsplit(" ", 1)
            hour, minute = map(int, time_part.split(":"))

            if period == "PM" and hour != 12:
                hour += 12
            elif period == "AM" and hour == 12:
                hour = 0

            return hour * 60 + minute

        return (time_to_minutes(start_str), time_to_minutes(end_str))
    except Exception:
        return None


def parse_section_times(
    times_str: str, days_str: str
) -> Dict[str, List[Tuple[int, int]]]:
    """Map times to days. Returns dict of day -> [(start, end), ...]."""
    if not times_str or not days_str:
        return {}

    day_to_times = {}
    time_slots = [slot.strip() for slot in times_str.split(",")]

    # If single time slot, apply to all days
    if len(time_slots) == 1:
        parsed = parse_time_str(time_slots[0])
        if parsed:
            for day in days_str:
                day_to_times[day] = [parsed]
    else:
        # Multiple time slots - map to days in order
        for i, day in enumerate(days_str):
            if i < len(time_slots):
                parsed = parse_time_str(time_slots[i])
                if parsed:
                    day_to_times[day] = [parsed]

    return day_to_times


def has_time_conflict(section1_times: Dict, section2_times: Dict) -> bool:
    """Check if two sections have overlapping times on any shared day."""
    for day in section1_times:
        if day not in section2_times:
            continue

        # Check all time slot pairs for this day
        for start1, end1 in section1_times[day]:
            for start2, end2 in section2_times[day]:
                # Check for overlap: ranges overlap if start1 < end2 and start2 < end1
                if start1 < end2 and start2 < end1:
                    return True

    return False


def get_tools(user_prereqs: UserFulfilled, term: TERMS):
    def course_query(args: CourseQueryFormat) -> List[Dict[str, Any]]:
        """
        Queries the course database for semantic similarities.

        Args:
            {
            "query": "Natural language description of the course(s) the user is searching for.",
            "top_n": "Maximum number of courses to return, ordered by relevance.",
            "only_prereqs_fulfilled": "If true, returns only courses for which the user satisfies all prerequisites. If false, returns all relevant courses regardless of prerequisites.",
            "only_current_semester": "If true, only looks at courses offered in current semester. If false, looks at all courses."
            }

        Returns:
            Top_n matching courses based on query and only_prereqs_fulfilled.
        """
        print("DEBUG:", args.model_dump())
        query_text = args.query
        n = args.top_n

        # Fetch significantly more candidates for the cross-encoder to re-rank
        # This ensures we don't miss relevant items that have lower vector scores
        fetch_k = 500

        try:
            results = collection.query(
                ids=get_available_courses(
                    user_prereqs,
                    args.only_prereqs_fulfilled,
                    args.only_current_semester,
                    term,
                ),
                query_texts=[query_text],
                n_results=fetch_k,
            )

            if not results["ids"]:
                return []

            flat_results: List[Dict[str, Any]] = []
            ids_list = results["ids"][0]
            distances_list = (
                results["distances"][0]
                if results["distances"]
                else [None] * len(ids_list)
            )
            metadatas_list = (
                results["metadatas"][0]
                if results["metadatas"]
                else [None] * len(ids_list)
            )
            documents_list = (
                results["documents"][0]
                if results["documents"]
                else [None] * len(ids_list)
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

                flat_results.sort(key=lambda x: x["score"], reverse=True)

            return {
                "search_result": flat_results[:n],
                "message_to_relay_to_user": "Configuration: Results restricted to current term."
                if args.only_current_semester
                else "Configuration: Results not restricted to current term.",
            }

        except Exception as e:
            print("Error querying ChromaDB:", e)
            return []

    def update_user_profile(args: UpdateUserProfile):
        """
        Updates the user profile.

        Args:
            {
            "courses": {
                        "name": "course name", "grade": ""Grade recieved in course. A pass is a 'C'. Example: 'I passed a class', then grade = 'C'."
                        },
            "equivalents": "List of courses that the user has equivalents for. Example: (equivalents for CS 350).",
            "standing": "User's academic standing (FRESHMAN, SOPHOMORE, JUNIOR, SENIOR, GRAD).",
            "semesters_left": "Number of semesters remaining until graduation.",
            "to_remove": {
                        "courses": "List of courses to remove.",
                        "equivalents": "List of courses equivalents to remove.",
                        "remove_standing": "Whether to remove standing from profile.",
                        "remove_semesters_left": "Whether to remove semesters_left from profile."
                        }
            }

        Returns:
            All user fullfilments after current update and errors if any.
        """
        print("DEBUG:", args.model_dump())
        errors = []
        for course in args.courses:
            course_name = normalize_course(course.name)
            # TODO: make it so that the valid ones are added.
            if isinstance(course_name, dict):
                errors.append(course_name)
                continue
            user_prereqs.courses[course_name] = course

        for eq in args.equivalents:
            course_name = normalize_course(eq)
            if isinstance(course_name, dict):
                errors.append(course_name)
                continue
            user_prereqs.equivalents.append(course_name)

        if args.standing:
            user_prereqs.standing = args.standing
        if args.semesters_left:
            user_prereqs.semesters_left = args.semesters_left

        to_remove = args.to_remove
        if to_remove:
            for course in to_remove.courses:
                if course in user_prereqs.courses.keys():
                    del user_prereqs.courses[course]
                else:
                    errors.append(
                        {"error_message": f"{course} was not found in user courses!"}
                    )

            for equivalent in to_remove.equivalents:
                if equivalent in user_prereqs.equivalents:
                    user_prereqs.equivalents.remove(equivalent)
                else:
                    errors.append(
                        {
                            "error_message": f"{course} was not found in user equivalents!"
                        }
                    )

            if to_remove.standing:
                user_prereqs.standing = None

            if to_remove.semesters_left:
                user_prereqs.semesters_left = None

        return user_prereqs.model_dump()

    def get_course_description(args: CourseSearchFormat) -> str:
        """
        Gets the course description of a course.

        Args:
            {
            "course_name": "Name of the course to search for."
            }

        Returns:
            description of the course
        """
        print("DEBUG:", args.model_dump())
        res = normalize_course(args.course_name)
        if isinstance(res, dict):
            return res
        course_name = res

        return course_data[course_name].desc

    def can_take_course(args: CourseSearchFormat) -> bool | str:
        """
        Checks if user can take a course.

        Args:
            {
            "course_name": "Name of the course to search for."
            }

        Returns:
            True or explanation of why user can't take it
        """
        print("DEBUG:", args.model_dump())
        res = normalize_course(args.course_name)
        if isinstance(res, dict):
            return res
        course_name = res

        if course_name in user_prereqs.courses:
            return f"You have already completed or are currently taking {course_name}."

        course_info = course_data[course_name]
        return check_prereq_tree(course_info.prereq_tree, user_prereqs)

    def make_schedule(args: MakeScheduleFormat) -> Dict[str, Any]:
        """
        Generates all possible schedules for the given courses that fit within the max_days constraint.

        Args:
            {
            "courses": "List of course names to include in the schedule.",
            "max_days": "Maximum number of days per week the user wants to attend classes (1-5)."
            }

        Returns:
            A list of valid schedules (each is a list of section selections) and any errors encountered.
        """

        print("DEBUG:", args.model_dump())
        errors = []
        valid_courses = []

        for course_name in args.courses:
            normalized = normalize_course(course_name)
            if isinstance(normalized, dict):
                errors.append(normalized)
            else:
                valid_courses.append(normalized)

        if not valid_courses:
            return {
                "errors": errors,
                "schedules": [],
                "message": "No valid courses provided.",
            }

        course_sections_list = []
        for course_name in valid_courses:
            course_info = course_data[course_name]
            if not course_info:
                errors.append(
                    {"error_message": f"Course data not found for {course_name}"}
                )
                continue

            term_sections = course_info.sections.get(term)
            if not term_sections:
                errors.append(
                    {
                        "error_message": f"No sections available for {course_name} in term {term}"
                    }
                )
                continue

            sections_for_course = []
            for section_id, section_data in term_sections.items():
                days = section_data[2]
                times = section_data[3]

                section_info = {
                    "course": course_name,
                    "section_id": section_id,
                    "days": days,
                    "crn": section_data[1],
                    "times": times,
                    "location": section_data[4],
                    "instructor": section_data[8],
                }

                # Parse and store time mappings
                section_info["parsed_times"] = parse_section_times(times, days)
                sections_for_course.append(section_info)

            if sections_for_course:
                course_sections_list.append(sections_for_course)
            else:
                errors.append(
                    {"error_message": f"No sections with day info for {course_name}"}
                )

        if not course_sections_list:
            return {
                "errors": errors,
                "schedules": [],
                "message": "No sections available for any valid course.",
            }

        all_combinations = list(itertools.product(*course_sections_list))

        valid_schedules = []
        for combo in all_combinations:
            unique_days = set()
            for section in combo:
                for day_char in section["days"]:
                    unique_days.add(day_char)

            # Check day constraint
            if len(unique_days) > args.max_days:
                continue

            # Check for time conflicts
            has_conflict = False
            for i in range(len(combo)):
                for j in range(i + 1, len(combo)):
                    if has_time_conflict(
                        combo[i]["parsed_times"], combo[j]["parsed_times"]
                    ):
                        has_conflict = True
                        break
                if has_conflict:
                    break

            if not has_conflict:
                # Remove parsed_times from output (internal use only)
                clean_sections = []
                for section in combo:
                    clean_section = {
                        k: v for k, v in section.items() if k != "parsed_times"
                    }
                    clean_sections.append(clean_section)

                valid_schedules.append(
                    {
                        "sections": clean_sections,
                        "days_used": sorted(list(unique_days)),
                        "num_days": len(unique_days),
                    }
                )

        return {
            "errors": errors if errors else None,
            "schedules": valid_schedules,
            "total_valid_schedules": len(valid_schedules),
            "message": f"Found {len(valid_schedules)} schedule(s) fitting within {args.max_days} day(s) with no time conflicts.",
        }

    return [
        course_query,
        update_user_profile,
        get_course_description,
        can_take_course,
        make_schedule,
    ]


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


def gemini_call(input_text: str, session_id: str, term: TERMS):
    client = genai.Client()

    history_raw = REDIS.get(f"{session_id}:history")
    prereqs_raw = REDIS.get(f"{session_id}:prereqs")
    history = load_history(history_raw)
    parsed_userprereqs = load_prereqs(prereqs_raw)
    tools = get_tools(parsed_userprereqs, term)

    # move to constants as global var
    with open(CHATBOT_PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt = f.read()
        
    sys_instruction = f"User's current profile: {prereqs_raw}." + prompt

    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False
            ),
        ),
        history=history,
    )

    response = chat.send_message(input_text)

    REDIS.set(f"{session_id}:history", dump_history(chat._curated_history))
    REDIS.set(f"{session_id}:prereqs", dump_prereqs(parsed_userprereqs))
    return response.text
