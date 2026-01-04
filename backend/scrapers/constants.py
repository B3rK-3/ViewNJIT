from backend.constants import BASE_PROMPTS_DIR
from backend.constants import LOGS_DIR
import os
import logging

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "scrapers.log"),
    format="%(asctime)s - %(levelname)s: %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.DEBUG,
)
logger = logging.getLogger("scrapers")

BASE_SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
TERM_FILE_PATH = os.path.join(BASE_SCRAPER_DIR, "currentTerm.txt")
DESCRIPTION_PROCESS_PROMPT_FILE = os.path.join(
    BASE_PROMPTS_DIR, "description_process_prompt.txt"
)

DEFAULT_RATING = {
    "avgRating": "0",
    "wouldTakeAgainPercent": "0",
    "avgDifficulty": "5",
    "link": "https://www.ratemyprofessors.com/teacher-not-found",
    "numRatings": "0",
    "legacyId": 0,
    "last_updated": 0,
}
CACHE_EXPIRATION_SECONDS = 5 * 60 * 60  # 5 hours
