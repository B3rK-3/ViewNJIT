from backend.types import CourseDataType
from backend.constants import COURSE_DATA
from backend.functions import construct_term_courses
from backend.constants import LECTURER_DATA
from backend.functions import (
    initialize_database,
    set_local_data,
    gemini_call_stream,
)
from backend.types import (
    ProfsResponse,
    ProfsRequest,
    ChatRequest,
)
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import json


app = FastAPI()
origins = ["http://localhost:3000", "https://flownjit.com", "https://www.flownjit.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=5)


@app.on_event("startup")
def startup():
    from backend.constants import warmup_constants

    warmup_constants()

    initialize_database()
    set_local_data()
    construct_term_courses()


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    async def generate():
        async for chunk in gemini_call_stream(
            request.query, request.sessionID, request.term, request.attachments
        ):
            yield json.dumps(chunk) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/getprofs", response_model=ProfsResponse)
async def prof_endpoint(request: ProfsRequest):
    results = {}
    for prof in request.profs:
        results[prof] = None
        if prof in LECTURER_DATA:
            results[prof] = LECTURER_DATA[prof]
    return results


@app.get("/getcourses", response_model=CourseDataType)
async def course_endpoint():
    return COURSE_DATA


def start():
    uvicorn.run(app, host="127.0.0.1", port=3001)


if __name__ == "__main__":
    start()
