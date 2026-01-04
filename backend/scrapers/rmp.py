import json
import requests
import time
from functools import cache
from backend.scrapers.constants import DEFAULT_RATING, CACHE_EXPIRATION_SECONDS, logger
from backend.constants import (
    COURSE_DATA,
    REDIS,
    REDIS_LECTURERS_KEY,
    LECTURERS_DATA_FILE,
)


@cache
def sync_lecturer_rating(lecturer_name: str, existing_data: dict = None):
    """
    Fetches the rating for a lecturer from the proxy API and updates Redis.
    lecturer_name format: "Lastname, Firstname"
    existing_data: optional already-loaded rating from Redis to avoid extra lookup
    """
    if not lecturer_name:
        return

    # Check cache
    if existing_data is None:
        raw_data = REDIS.hget(REDIS_LECTURERS_KEY, lecturer_name)
        if raw_data:
            try:
                existing_data = json.loads(raw_data)
            except Exception:
                existing_data = None

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

        # Save to Redis
        REDIS.hset(REDIS_LECTURERS_KEY, lecturer_name, json.dumps(rating))

        logger.info(f"Updated rating for {lecturer_name}")

    except Exception as e:
        logger.error(f"Error syncing rating for {lecturer_name}: {e}")


def check_all_lecturers():
    """
    Checks all lecturers found in course data and updates their ratings in Redis if expired.
    Uses pipelining for efficient batch operations.
    """
    # Collect all unique lecturers
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

    # Fetch all existing data at once to avoid N lookups
    all_current_data = REDIS.hgetall(REDIS_LECTURERS_KEY)

    for i, lecturer in enumerate(lecturers_list):
        # Get existing data from our bulk fetch
        raw_existing = all_current_data.get(lecturer)
        existing_obj = None
        if raw_existing:
            try:
                existing_obj = json.loads(raw_existing)
            except Exception:
                pass

        # Syncing rating will update Redis if needed
        sync_lecturer_rating(lecturer, existing_data=existing_obj)

        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i + 1}/{len(lecturers_list)} lecturers...")

    # Save final results back to file for persistence
    try:
        all_data = REDIS.hgetall(REDIS_LECTURERS_KEY)
        final_json = {}
        for name, rating_str in all_data.items():
            final_json[name] = json.loads(rating_str)

        with open(LECTURERS_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=4)
        logger.info(f"Saved {len(final_json)} lecturers back to {LECTURERS_DATA_FILE}")
    except Exception as e:
        logger.error(f"Error saving lecturer data to file: {e}")


if __name__ == "__main__":
    check_all_lecturers()
