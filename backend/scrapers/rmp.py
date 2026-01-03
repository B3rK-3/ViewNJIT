import json
import requests
import os
from backend.constants import LECTURERS_FILE
from functools import cache

DEFAULT_RATING = {
    "avgRating": "0",
    "wouldTakeAgainPercent": "0",
    "avgDifficulty": "5",
    "link": "error",
    "numRatings": "0",
    "legacyId": 0,
}


@cache
def sync_lecturer_rating(lecturer_name: str):
    """
    Fetches the rating for a lecturer from the proxy API and updates lecturers.json.
    lecturer_name format: "Lastname, Firstname"
    """
    if not lecturer_name:
        return

    print(f"Syncing rating for: {lecturer_name}")

    try:
        if ", " in lecturer_name:
            lastname, firstname = lecturer_name.split(", ", 1)
            query = f"{firstname} {lastname}"
        else:
            query = lecturer_name

        response = requests.get(
            f"https://backend-server-black-phi.vercel.app/prof?q={query}", timeout=10
        )

        if not response.ok or response.status_code == 204:
            rating = DEFAULT_RATING
        else:
            rating = response.json()

        # Update lecturers.json
        lecturer_ratings = {}
        if os.path.exists(LECTURERS_FILE):
            try:
                with open(LECTURERS_FILE, "r", encoding="utf-8") as f:
                    lecturer_ratings = json.load(f)
            except Exception as e:
                print(f"Error loading {LECTURERS_FILE}: {e}")

        lecturer_ratings[lecturer_name] = rating

        with open(LECTURERS_FILE, "w", encoding="utf-8") as f:
            json.dump(lecturer_ratings, f, indent=4, ensure_ascii=False)

        print(f"✓ Updated rating for {lecturer_name}")

    except Exception as e:
        print(f"Error syncing rating for {lecturer_name}: {e}")


if __name__ == "__main__":
    # Original behavior for backward compatibility or direct execution
    from backend.constants import course_data

    lecturers = []
    for course, course_info in course_data.items():
        for term in course_info.sections:
            for section_id in course_info.sections[term]:
                # In the original script, it was index -5.
                # SectionEntries = Tuple[str, str, str, str, str, str, str, str, str, str, str, str, str]
                # Instructor is at index 8 (0-based) which is -5 from the end (13 total)
                lecturer = course_info.sections[term][section_id][8]
                if lecturer and lecturer not in lecturers:
                    lecturers.append(lecturer)

    for i, lecturer in enumerate(lecturers):
        print(f"{i + 1} / {len(lecturers)}")
        sync_lecturer_rating(lecturer)
