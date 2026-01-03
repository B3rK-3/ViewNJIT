from backend.functions import initialize_database
from backend.functions import gemini_call
from backend.constants import ChatRequest
from backend.constants import ChatResponse
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from backend.constants import GEMINI_API_KEY

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


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    response = await run_in_threadpool(
        gemini_call, request.query, request.sessionID, request.term
    )
    return {"response": response}


def start():
    uvicorn.run(app, host="127.0.0.1", port=3001)


if __name__ == "__main__":
    start()
