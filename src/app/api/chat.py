"""Chat endpoint for RAG-powered Q&A."""

from typing import List, Optional
from pydantic import BaseModel
from ..rag.gemini import (
    generate_query_embedding,
    generate_answer,
    classify_message,
    generate_conversational_response,
)
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
        # Use AI to classify if message needs RAG search
        if not classify_message(message):
            # Conversational message - respond without RAG
            response = generate_conversational_response(message)
            return {
                "answer": response,
                "sources": [],
            }

        # Generate embedding for the query
        query_embedding = generate_query_embedding(message)

        # Retrieve relevant Q&A
        similar = self.retriever.search_similar(query_embedding, limit=10)

        # Debug: print all relevance scores
        print(f"[DEBUG] Query: {message}")
        print(f"[DEBUG] Found {len(similar)} results:")
        for s in similar[:5]:
            print(f"  - {s['relevance']:.2%}: {s['title'][:50]}...")

        # Filter by minimum relevance threshold
        MIN_RELEVANCE = 0.65
        relevant = [s for s in similar if s["relevance"] >= MIN_RELEVANCE][:5]

        if not relevant:
            return {
                "answer": "Kechirasiz, bu savol bo'yicha aniq ma'lumot topilmadi. ",
                "sources": [],
            }

        # Generate answer using Gemini
        history_dicts = None
        if history:
            history_dicts = [
                {"role": h["role"], "content": h["content"]} for h in history
            ]

        answer = generate_answer(message, relevant, history_dicts)

        # Build sources list
        sources = [
            {
                "id": item["id"],
                "title": item["title"],
                "relevance": round(item["relevance"], 2),
            }
            for item in relevant
        ]

        return {
            "answer": answer,
            "sources": sources,
        }
