"""FastAPI application for AskAI Q&A search."""

import time
from fastapi import FastAPI, Query, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
from .search import SearchService
from .chat import ChatService, ChatMessage
from ..database.db import Database

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


def detect_device_type(user_agent: str) -> str:
    """Detect device type from user agent string."""
    if not user_agent:
        return "desktop"
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        return "tablet"
    return "desktop"


def parse_language(accept_language: str) -> Optional[str]:
    """Parse primary language from Accept-Language header."""
    if not accept_language:
        return None
    # e.g., "uz,ru;q=0.9,en;q=0.8" -> "uz"
    return accept_language.split(",")[0].split(";")[0].strip()


# Chat request/response models
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


class Source(BaseModel):
    id: int
    title: str
    relevance: float


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    source_type: str  # "database", "ai_knowledge", "conversational"
    disclaimer: Optional[str] = None


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


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    x_session_id: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
    accept_language: Optional[str] = Header(None),
):
    """Chat with the AI assistant using RAG.

    Returns answer with source_type:
    - "database": Answer from DB sources (shows sources)
    - "ai_knowledge": AI-generated answer (shows disclaimer)
    - "conversational": Simple greeting/response
    """
    start_time = time.time()

    history_dicts = None
    if request.history:
        history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

    result = chat_service.chat(request.message, history_dicts)

    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)

    # Save session and chat if session_id provided
    if x_session_id:
        try:
            db = Database()

            # Detect device type from user agent
            device_type = detect_device_type(user_agent)

            # Parse primary language
            language = parse_language(accept_language)

            # Get client IP
            ip_address = http_request.client.host if http_request.client else None

            # Upsert session
            db.upsert_session(
                session_id=x_session_id,
                user_agent=user_agent,
                device_type=device_type,
                language=language,
                ip_address=ip_address,
            )

            # Extract keywords (internal field, not returned to client)
            keywords = result.get("_keywords", [])

            # Save chat message
            db.insert_chat_message(
                session_id=x_session_id,
                question=request.message,
                answer=result["answer"],
                source_type=result["source_type"],
                sources=result.get("sources", []),
                keywords=keywords,
                response_time_ms=response_time_ms,
            )

            db.close()
        except Exception as e:
            # Don't fail the request if session save fails
            print(f"[WARNING] Failed to save session/chat: {e}")

    # Remove internal _keywords field before returning
    result.pop("_keywords", None)

    return result


@app.get("/api/chat/history/{session_id}")
def get_chat_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum messages to return"),
):
    """Get chat history for a session."""
    db = Database()
    try:
        messages = db.get_chat_history(session_id, limit)
        return {"messages": messages}
    finally:
        db.close()
