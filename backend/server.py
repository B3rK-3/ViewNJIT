from backend.functions import set_redis_course_data
from backend.constants import (
    REDIS_LECTURERS_KEY,
    REDIS,
    ProfsResponse,
    ProfsRequest,
    COURSE_DATA_FILE,
    ChatRequest,
    ChatResponse,
)
from backend.functions import initialize_database, gemini_call, set_redis_lecturer_data
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


@app.on_event("startup")
def start_scrapers():
    set_redis_lecturer_data()
    set_redis_course_data()
    start_background_scrapers()


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    response = await run_in_threadpool(
        gemini_call, request.query, request.sessionID, request.term
    )
    return {"response": response}


@app.post("/getprofs", response_model=ProfsResponse)
async def prof_endpoint(request: ProfsRequest):
    results = REDIS.hmget(REDIS_LECTURERS_KEY, request.profs)
    for i, result in enumerate(results):
        if result:
            results[i] = json.loads(result)
    return dict(zip(request.profs, results))


def start():
    uvicorn.run(app, host="127.0.0.1", port=3001)


if __name__ == "__main__":
    start()
