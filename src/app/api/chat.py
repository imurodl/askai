"""Chat endpoint for RAG-powered Q&A."""

from typing import List, Optional
from pydantic import BaseModel
from ..rag.gemini import generate_query_embedding, generate_answer
from ..rag.retriever import Retriever


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


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


class ChatService:
    """Service for RAG-powered chat."""

    def __init__(self):
        self.retriever = Retriever()

    def chat(self, message: str, history: Optional[List[dict]] = None) -> dict:
        """Process a chat message and return AI-generated answer.

        Args:
            message: User's question
            history: Optional conversation history

        Returns:
            Dict with answer and sources
        """
        # Generate embedding for the query
        query_embedding = generate_query_embedding(message)

        # Retrieve relevant Q&A
        similar = self.retriever.search_similar(query_embedding, limit=5)

        if not similar:
            return {
                "answer": "Kechirasiz, bu savol bo'yicha ma'lumot topilmadi.",
                "sources": [],
            }

        # Generate answer using Gemini
        history_dicts = None
        if history:
            history_dicts = [{"role": h["role"], "content": h["content"]} for h in history]

        answer = generate_answer(message, similar, history_dicts)

        # Build sources list
        sources = [
            {
                "id": item["id"],
                "title": item["title"],
                "relevance": round(item["relevance"], 2),
            }
            for item in similar
        ]

        return {
            "answer": answer,
            "sources": sources,
        }
