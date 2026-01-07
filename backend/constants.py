from backend.types import LecturerRatingType
from backend.types import CourseDataType
import os
from typing import List, Dict, Set
import dotenv
from backend.types import CourseInfoModel, LecturerRating

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load dotenv before reading any env vars
dotenv.load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_KEY = os.getenv("CHROMA_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DB = os.getenv("CHROMA_DB")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
COURSE_DATA_FILE = os.path.join(BASE_DIR, "data/graph.json")
BASE_PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
LECTURERS_DATA_FILE = os.path.join(BASE_DIR, "data/lecturers.json")
CHATBOT_PROMPT_FILE = os.path.join(BASE_PROMPTS_DIR, "chatbot_prompt.txt")

REDIS_LECTURERS_KEY = "lecturers"
REDIS_COURSES_KEY = "courses"
CHROMA_COLLECTION_NAME = "njit_courses"

STANDINGS = ["FRESHMAN", "SOPHOMORE", "JUNIOR", "SENIOR", "GRAD"]
SEMESTERS = {
    "10": "Spring",
    "90": "Fall",
    "95": "Winter",
    "50": "Summer",
}

# These are populated later by functions.py
COURSE_DATA: CourseDataType = {}
VALID_COURSE_NAMES: Set[str] = set()
LECTURER_DATA: LecturerRatingType = {}
term_courses: Dict[str, List[str]] = {}
MAX_CHAT_HISTORY_LEN = 5

# Internal state for lazy loading
_device = None
_ef = None
_CROSS_ENCODER = None
_CHROMA_CLIENT = None
_CHROMA_COLLECTION = None
_REDIS = None


def get_device():
    global _device
    if _device is None:
        from torch.cuda import is_available

        _device = "cuda" if is_available() else "cpu"
    return _device


def get_ef():
    global _ef
    if _ef is None:
        from chromadb.utils import embedding_functions

        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2", device=get_device()
        )
    return _ef


def get_cross_encoder():
    global _CROSS_ENCODER
    if _CROSS_ENCODER is None:
        from sentence_transformers import CrossEncoder

        _CROSS_ENCODER = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2", device=get_device()
        )
    return _CROSS_ENCODER


def get_chroma_client():
    global _CHROMA_CLIENT
    if _CHROMA_CLIENT is None:
        import chromadb

        _CHROMA_CLIENT = chromadb.PersistentClient(path="./chromadb")
    return _CHROMA_CLIENT


def get_chroma_collection():
    global _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is None:
        client = get_chroma_client()
        _CHROMA_COLLECTION = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME, embedding_function=get_ef()
        )
    return _CHROMA_COLLECTION


def get_redis():
    global _REDIS
    if _REDIS is None:
        import redis

        _REDIS = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    return _REDIS


def __getattr__(name):
    if name == "device":
        return get_device()
    if name == "ef":
        return get_ef()
    if name == "CROSS_ENCODER":
        return get_cross_encoder()
    if name == "CHROMA_CLIENT":
        return get_chroma_client()
    if name == "CHROMA_COLLECTION":
        return get_chroma_collection()
    if name == "REDIS":
        return get_redis()
    raise AttributeError(f"module {__name__} has no attribute {name}")


def warmup_constants():
    """Accesses all lazy properties to force initialization."""
    _ = get_device()
    _ = get_redis()
    _ = get_chroma_collection()
    _ = get_cross_encoder()
    print("Warmup complete: All models loaded into this worker's RAM.")