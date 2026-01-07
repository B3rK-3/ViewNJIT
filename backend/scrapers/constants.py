from backend.constants import LECTURERS_DATA_FILE
from backend.constants import COURSE_DATA_FILE
from backend.functions import set_redis_lecturer_data
from backend.functions import set_redis_course_data
from backend.constants import LOGS_DIR, BASE_PROMPTS_DIR, __getattr__
from backend.functions import get_redis_course_data, get_redis_lecturers_data
from backend.types import CourseStructureModel, LecturerStructureModel

import os
import logging
import json

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
REDIS = __getattr__("REDIS")

COURSE_DATA = get_redis_course_data() or set_redis_course_data(
    (CourseStructureModel.model_validate(json.load(open(COURSE_DATA_FILE, "r"))).root)
)
LECTURER_DATA = get_redis_lecturers_data() or set_redis_lecturer_data(
    (
        LecturerStructureModel.model_validate(
            json.load(open(LECTURERS_DATA_FILE, "r"))
        ).root
    )   
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
