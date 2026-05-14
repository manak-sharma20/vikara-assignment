from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# Run KB ingestion at startup so in-memory ChromaDB is populated
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up: ingesting knowledge base...")
    from knowledge_base.ingest import ingest_articles
    ingest_articles()
    print("✅ Knowledge base ready.")
    yield
    print("🛑 Shutting down.")

app = FastAPI(title="CloudDash Support API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions = {}

class MessageRequest(BaseModel):
    message: str

@app.get("/")
def serve_frontend():
    """Serve the chat frontend."""
    return FileResponse("index.html")

@app.post("/conversation/start")
def start_conversation():
    """Starts a new conversation session."""
    from agents.orchestrator import Orchestrator
    session_id = str(uuid.uuid4())
    sessions[session_id] = Orchestrator()
    return {
        "session_id": session_id,
        "message": "Hi! I'm CloudDash support. How can I help?"
    }

@app.post("/conversation/{session_id}/message")
def send_message(session_id: str, req: MessageRequest):
    """Sends a message to an existing session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    orchestrator = sessions[session_id]
    response = orchestrator.chat(req.message)
    
    return {
        "response": response,
        "agent": orchestrator.current_agent,
        "session_id": session_id
    }

@app.get("/conversation/{session_id}/history")
def get_history(session_id: str):
    """Gets the conversation history for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "history": sessions[session_id].conversation_history,
        "session_id": session_id
    }
