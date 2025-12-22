"""FastAPI application for AskAI Q&A search."""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
from .search import SearchService
from .chat import ChatService, ChatMessage

app = FastAPI(
    title="AskAI API",
    description="RAG-powered Islamic Q&A Chatbot API",
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_service = SearchService()
chat_service = ChatService()


# Chat request/response models
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


@app.get("/api/search")
def search_questions(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Search questions by keyword."""
    results = search_service.search(q, limit, offset)
    return results


@app.get("/api/questions/{question_id}")
def get_question(question_id: int):
    """Get a single question with its related questions."""
    question = search_service.get_question_by_id(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.get("/api/popular")
def get_popular_questions(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
):
    """Get popular questions sorted by view count."""
    results = search_service.get_popular(limit)
    return results


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest):
    """Chat with the AI assistant using RAG."""
    history_dicts = None
    if request.history:
        history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

    result = chat_service.chat(request.message, history_dicts)
    return result
