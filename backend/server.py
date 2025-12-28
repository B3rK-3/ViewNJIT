from functions import initialize_database
from functions import gemini_call
from constants import ChatRequest
from constants import ChatResponse
from fastapi import FastAPI, HTTPException
import uvicorn
from constants import GEMINI_API_KEY, current_session_id

app = FastAPI()
initialize_database()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    
    current_session_id.set(request.sessionID)
    response = gemini_call(request.query)
    return {"response": response}

    


if __name__ == "__main__":
    print(1)
    uvicorn.run(app, host="127.0.0.1", port=3001)
    print(2)
