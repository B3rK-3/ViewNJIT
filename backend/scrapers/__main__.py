import os
import threading
import time
from backend.scrapers.courses import scrape_courses
from backend.scrapers.rmp import check_all_lecturers
from backend.scrapers.constants import (
    TERM_FILE_PATH,
    logger,
    REDIS,
    LECTURER_DATA,
    COURSE_DATA,
)



def run_course_scraper():
    print('starting course scraper')
    while True:
        time.sleep(5 * 60)
        try:
            if not os.path.exists(TERM_FILE_PATH):
                logger.warning(f"{TERM_FILE_PATH} not found. Skipping course scrape.")
            else:
                with open(TERM_FILE_PATH, "r") as term_file:
                    term = term_file.read().strip()

                if term:
                    logger.info(f"--- Starting course scrape for term: {term} ---")
                    scrape_courses(term, sections=True)
                    REDIS.publish("course_updates", "refresh")
                    logger.info(
                        "--- Course scrape finished. Sleeping for 5 minutes. ---"
                    )
                else:
                    logger.warning(f"{TERM_FILE_PATH} is empty.")

        except Exception as e:
            logger.error(f"Error in Course Scraper: {e}")


def run_lecturer_check():
    print('starting lecturer check')
    while True:
        time.sleep(6 * 60 * 60)
        try:
            logger.info("--- Starting lecturer check ---")
            check_all_lecturers()
            REDIS.publish("lecturer_updates", "refresh")
            logger.info("--- Lecturer check finished. Sleeping for 6 hours. ---")

        except Exception as e:
            logger.error(f"Error in Lecturer Check: {e}")


def start_background_scrapers():
    # Create the thread objects
    thread1 = threading.Thread(target=run_course_scraper, daemon=True)
    thread2 = threading.Thread(target=run_lecturer_check, daemon=True)

    # Start the threads
    thread1.start()
    thread2.start()

    logger.info("Both scrapers are running in the background...")


if __name__ == "__main__":
    if not LECTURER_DATA:
        logger.error("LECTURER_DATA NOT LOADED!")
        raise Exception("LECTURER_DATA NOT LOADED!")
    if not COURSE_DATA:
        logger.error("COURSE_DATA NOT LOADED!")
        raise Exception("COURSE_DATA NOT LOADED!")

    start_background_scrapers()
    # Keep the main thread alive so the background threads don't die
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping all scrapers...")
