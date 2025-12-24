import json
import requests
from bs4 import BeautifulSoup
import time
import os


def scrape_prereqs():
    file_path = r"d:\Projects\NJIT_Course_FLOWCHART\njit_courses_output.json"

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Reading {file_path}...")
    with open(file_path, "r") as f:
        data = json.load(f)

    new_data = {}

    # Calculate total for progress tracking
    total_courses = sum(len(courses) for courses in data.values())
    current_count = 0

    print(f"Found {total_courses} courses. Starting scrape...")

    for subject, course_list in data.items():
        new_course_list = []
        for item in course_list:
            current_count += 1

            # Handle if item is string (first run) or dict (subsequent runs)
            if isinstance(item, str):
                course_code = item
                course_obj = {"course": course_code}
                print("WRONG:", item)
                continue
            elif isinstance(item, dict):
                course_code = item.get("course", "")
                course_obj = item
            else:
                continue

            print(
                f"[{current_count}/{total_courses}] Scraping {course_code}...", end="\r"
            )

            url = f"https://catalog.njit.edu/search/?P={course_code}"

            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Find a <p> field with 'Prerequisites:'
                    target_p = soup.find("p", class_="courseblockdesc")

                    if target_p:
                        full_text = target_p.get_text().strip()
                        # Find the first period to get the first sentence
                        sentence = full_text
                        course_obj["desc"] = sentence
                    else:
                        course_obj['desc'] = 'No Description'
            except Exception as e:
                # Fail silently or log if needed, but keep the course object
                pass

            new_course_list.append(course_obj)
            print(course_obj)
            # time.sleep(0.1)  # Rate limiting

        new_data[subject] = new_course_list

    print(f"\nWriting updates to {file_path}...")
    with open("njit_courses_output_v2.json", "w+") as f:
        json.dump(new_data, f, indent=4)
    print("Process complete.")


if __name__ == "__main__":
    scrape_prereqs()
