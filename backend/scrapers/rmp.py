import json
import requests
import time
from functools import cache
from backend.scrapers.constants import (
    DEFAULT_RATING,
    CACHE_EXPIRATION_SECONDS,
    logger,
    COURSE_DATA,
    LECTURER_DATA,
    set_redis_lecturer_data,
    LecturerStructureModel,
)
from backend.constants import LECTURERS_DATA_FILE


@cache
def sync_lecturer_rating(lecturer_name: str, existing_data: dict = None):
    """
    Fetches the rating for a lecturer from the proxy API and updates Redis.
    lecturer_name format: "Lastname, Firstname"
    existing_data: optional already-loaded rating from Redis to avoid extra lookup
    """
    if not lecturer_name:
        return

    if existing_data:
        last_updated = existing_data.get("last_updated", 0)
        if time.time() - last_updated < CACHE_EXPIRATION_SECONDS:
            return

    logger.debug(f"Syncing rating for: {lecturer_name}")

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
            rating = DEFAULT_RATING.copy()
        else:
            rating = response.json()

        # Update last_updated field
        rating["last_updated"] = time.time()

        logger.info(f"Returned rating for {lecturer_name}")
        return rating

    except Exception as e:
        logger.error(f"Error syncing rating for {lecturer_name}: {e}")


def check_all_lecturers():
    """
    Checks all lecturers found in course data and updates their ratings in Redis if expired.
    Uses pipelining for efficient batch operations.
    """
    # Collect all unique lecturers
    if not LECTURER_DATA:
        logger.error("LECTURER_DATA NOT LOADED!")
        return
    if not COURSE_DATA:
        logger.error("COURSE_DATA NOT LOADED!")
        return

    unique_lecturers = set()
    for course_info in COURSE_DATA.values():
        for term_sections in course_info.sections.values():
            for section in term_sections.values():
                # Instructor is at index 8
                lecturer = section[8]
                if lecturer:
                    unique_lecturers.add(lecturer)

    lecturers_list = sorted(list(unique_lecturers))
    logger.info(f"Found {len(lecturers_list)} unique lecturers to check.")

    for i, lecturer in enumerate(lecturers_list):
        # Get existing data from our bulk fetch
        existing_obj = LECTURER_DATA.get(lecturer)

        # Syncing rating will update Redis if needed
        new_rating = sync_lecturer_rating(
            lecturer_name=lecturer, existing_data=existing_obj
        )

        LECTURER_DATA[lecturer] = new_rating

        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i + 1}/{len(lecturers_list)} lecturers...")

    set_redis_lecturer_data(LECTURER_DATA)

    # for now update the file too
    with open(LECTURERS_DATA_FILE, "w") as f:
        json.dump(LecturerStructureModel(LECTURER_DATA).model_dump(), f, indent=4)


if __name__ == "__main__":
    if not LECTURER_DATA:
        raise Exception("LECTURER_DATA NOT LOADED!")
    if not COURSE_DATA:
        raise Exception("COURSE_DATA NOT LOADED!")
    check_all_lecturers()
