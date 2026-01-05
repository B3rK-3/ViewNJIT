from backend.constants import LECTURER_DATA
from backend.constants import (
    REDIS_LECTURERS_KEY,
    REDIS,
    ProfsResponse,
    ProfsRequest,
    ChatRequest,
    ChatResponse,
)
from backend.functions import (
    initialize_database,
    gemini_call,
    set_local_lecturers_data,
    set_local_course_data,
)
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from backend.scrapers.__main__ import start_background_scrapers
import json

app = FastAPI()
origins = ["http://localhost:3000", "https://flownjit.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
initialize_database()
set_local_lecturers_data()
set_local_course_data()


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    response = await run_in_threadpool(
        gemini_call, request.query, request.sessionID, request.term
    )
    return {"response": response}


@app.post("/getprofs", response_model=ProfsResponse)
async def prof_endpoint(request: ProfsRequest):
    results = {}
    for prof in request.profs:
        results[prof] = None
        if prof in LECTURER_DATA:
            results[prof] = LECTURER_DATA[prof]
    return results


def start():
    uvicorn.run(app, host="127.0.0.1", port=3001, workers=4)


if __name__ == "__main__":
    start()
