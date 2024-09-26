import os
import uvicorn
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse,JSONResponse
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(level=logging.INFO)

from modules import Modules

api_key_header = APIKeyHeader(name='Authorization', auto_error=False)
token = os.environ['TOKEN']
modules = None

async def get_token(api_key: str = Depends(api_key_header)):
    if api_key != f"Bearer {token}":
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key",
        )
    return api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    global modules
    logging.info("Initializing Modules...")
    modules = Modules()
    logging.info("Modules initialized.")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def reply():
    json_compatible_item_data = {"hello" : "world"}
    return JSONResponse(content=json_compatible_item_data)

@app.post("/v1/api/chat")
async def answer(data: dict, api_key: str = Depends(get_token)) -> StreamingResponse:
    if 'question' not in data:
        raise HTTPException(status_code=400, detail="question field is missing")
    if 'session_id' not in data:
        raise HTTPException(status_code=400, detail="session_id field is missing")  
    if 'id' not in data:
        raise HTTPException(status_code=400, detail="id field is missing")  
    if 'acc_rec' not in data:
        raise HTTPException(status_code=400, detail="acc_rec field is missing")  
    
    return StreamingResponse(
        modules.chatbot.chat(data['question'], data['session_id'], data['id'], data['acc_rec']), 
        media_type="text/event-stream")

@app.post("/v1/api/chat_prompt")
async def answer_prompt(data: dict, api_key: str = Depends(get_token)) -> Dict[str, Any]:
    if 'question' not in data:
        raise HTTPException(status_code=400, detail="question field is missing")
    if 'session_id' not in data:
        raise HTTPException(status_code=400, detail="session_id field is missing")  
    if 'id' not in data:
        raise HTTPException(status_code=400, detail="id field is missing")  
    if 'acc_rec' not in data:
        raise HTTPException(status_code=400, detail="acc_rec field is missing")  
    answer = await modules.chatbot.chat_prompt_answer(data['question'], data['session_id'], data['id'], data['acc_rec'])
    return JSONResponse(content=answer)

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        workers=1,
        host="0.0.0.0",
        port=8080,
        ssl_keyfile="/home/ai_dev/applications/case-advisor-ai/certs/private_key.pem",
        ssl_certfile="/home/ai_dev/applications/case-advisor-ai/certs/certificate.pem")