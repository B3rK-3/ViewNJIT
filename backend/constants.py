import os
from typing import List, Dict, Union, Optional, Literal, Tuple, Any, Annotated
from pydantic import BaseModel, RootModel, ConfigDict, Field
import dotenv
import redis
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder
import chromadb
from torch.cuda import is_available
from backend.types import CourseInfoModel, LecturerRating


device = "cpu"
if is_available():
    device = "cuda"
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2", device=device
)

CROSS_ENCODER = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device=device)

CHROMA_CLIENT = chromadb.PersistentClient(path="./chromadb")

CHROMA_COLLECTION_NAME = "njit_courses"
CHROMA_COLLECTION = CHROMA_CLIENT.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME, embedding_function=ef
)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_KEY = os.getenv("CHROMA_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DB = os.getenv("CHROMA_DB")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
COURSE_DATA_FILE = os.path.join(BASE_DIR, "data/graph.json")
BASE_PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
REDIS = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
LECTURERS_DATA_FILE = os.path.join(BASE_DIR, "data/lecturers.json")
CHATBOT_PROMPT_FILE = os.path.join(BASE_PROMPTS_DIR, "chatbot_prompt.txt")

REDIS_LECTURERS_KEY = "lecturers"
REDIS_COURSES_KEY = "courses"

dotenv.load_dotenv(os.path.join(BASE_DIR, ".env"))

# SectionsEntries = Section	    CRN	    Days [Monday-M, Tuesday-T, Wednesday-W, Thursday-R, Friday-F]+	Times	Location	Status	Max	Now	Instructor	Delivery Mode	Credits	Info	Comments

STANDINGS = ["FRESHMAN", "SOPHOMORE", "JUNIOR", "SENIOR", "GRAD"]
SEMESTERS = {
    "10": "Spring",
    "90": "Fall",
    "95": "Winter",
    "50": "Summer",
}

COURSE_DATA: Dict[str, CourseInfoModel] = {}
VALID_COURSE_NAMES = set()
LECTURER_DATA: Dict[str, LecturerRating] = {}

term_courses = {}
CHAT_N = 5
