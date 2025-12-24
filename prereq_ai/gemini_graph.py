import json
import os
import time
import dotenv
from google import genai
from google.genai import types

dotenv.load_dotenv()


def create_graph_json():
    # File Paths
    courses_file = r"d:\Projects\NJIT_Course_FLOWCHART\data\njit_courses.json"
    prompt_file = r"d:\Projects\NJIT_Course_FLOWCHART\prompt.txt"
    output_file = r"d:\Projects\NJIT_Course_FLOWCHART\graph_v1.json"

    # Check for API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please set it using: set GEMINI_API_KEY=your_api_key_here")
        return

    # Configure Gemini
    client = genai.Client(api_key=api_key)

    # Load Data
    if not os.path.exists(courses_file):
        print(f"File not found: {courses_file}")
        return

    print("Loading courses and prompt...")
    with open(courses_file, "r") as f:
        courses_data = json.load(f)

    with open(prompt_file, "r", encoding='utf-8') as f:
        prompt_template = f.read()

    graph_output = {}

    # Collect all courses that have prerequisites
    courses_to_process = []
    for subject, course_list in courses_data.items():
        for course_obj in course_list:
            if "desc" in course_obj:
                courses_to_process.append(course_obj)

    total_courses = len(courses_to_process)
    print(f"Found {total_courses} courses with prerequisites.")

    # Process each course
    for i, course_obj in enumerate(courses_to_process):
        course_code = course_obj.get("course")
        prereq_text = course_obj.get("desc")

        if not course_code.startswith("MATH 477"):
            continue

        print(f"[{i + 1}/{total_courses}] Processing {course_code}...", end="\r")

        # Inject text into prompt
        final_prompt = prompt_template + '\n INPUT: ' + prereq_text

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=final_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

            # Parse JSON response
            try:
                parsed_json = json.loads(response.text)
                print(course_code, ":", parsed_json)
                parsed_json["desc"] = prereq_text
                print(prereq_text)
                print()
                graph_output[course_code] = parsed_json
            except json.JSONDecodeError:
                print(f"\nError parsing JSON for {course_code}. Raw output saved.")
                graph_output[course_code] = {
                    "error": "JSON Parse Error",
                    "raw_response": response.text,
                }

        except Exception as e:
            print(f"\nAPI Error on {course_code}: {e}")
            time.sleep(5)  # Backoff on error

        time.sleep(1)  # Rate limiting

    print(f"\nSaving results to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(graph_output, f, indent=4)
    print("Process complete.")


if __name__ == "__main__":
    create_graph_json()
