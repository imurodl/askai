"""Chat endpoint for RAG-powered Q&A."""

from typing import List, Optional
from pydantic import BaseModel
from ..rag.gemini import (
    generate_query_embedding,
    generate_answer,
    classify_message,
    generate_conversational_response,
    extract_search_keywords,
    generate_fallback_answer,
)
from ..rag.retriever import Retriever
from .search import SearchService


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
    source_type: str  # "database", "ai_knowledge", "conversational"
    disclaimer: Optional[str] = None


class ChatService:
    """Service for RAG-powered chat."""

    def __init__(self):
        self.retriever = Retriever()
        self.search_service = SearchService()

    def chat(self, message: str, history: Optional[List[dict]] = None) -> dict:
        """Process a chat message and return AI-generated answer.

        New flow:
        1. Classify message (conversational vs question)
        2. Extract keywords using AI (handles transliteration + Islamic terms)
        3. Keyword search first (fast, accurate)
        4. Embedding fallback if keyword search insufficient
        5. Generate answer from sources OR fallback to AI knowledge

        Args:
            message: User's question
            history: Optional conversation history

        Returns:
            Dict with answer, sources, source_type, and optional disclaimer
        """
        # Step 1: Classify message
        # If there's history, treat follow-ups as continuations (use AI with context)
        has_history = history and len(history) > 0
        is_question = classify_message(message)

        if not is_question and not has_history:
            # Pure conversational (greeting, etc.) without context
            response = generate_conversational_response(message)
            return {
                "answer": response,
                "sources": [],
                "source_type": "conversational",
            }

        if not is_question and has_history:
            # Follow-up request (like "make it shorter") - use AI with history
            history_dicts = [{"role": h["role"], "content": h["content"]} for h in history]
            fallback_result = generate_fallback_answer(message, history_dicts)
            return {
                "answer": fallback_result["answer"],
                "sources": [],
                "source_type": "ai_knowledge",
                "disclaimer": fallback_result["disclaimer"],
            }

        # Step 2: Extract keywords using AI
        print(f"[DEBUG] Original query: {message}")
        keyword_result = extract_search_keywords(message)
        print(f"[DEBUG] Extracted keywords: {keyword_result}")

        all_keywords = (
            keyword_result["primary_keywords"] +
            keyword_result["related_keywords"]
        )

        # Step 3: Keyword search first
        keyword_results = []
        if all_keywords:
            keyword_results = self.search_service.search_by_keywords(
                all_keywords,
                limit=10
            )
            print(f"[DEBUG] Keyword search found {len(keyword_results)} results")
            for r in keyword_results[:3]:
                print(f"  - score={r.get('match_score', 0)}: {r['title'][:50]}...")

        # Step 4: Embedding fallback if keyword search insufficient
        if len(keyword_results) < 3:
            rewritten_query = keyword_result["rewritten_query"]
            print(f"[DEBUG] Trying embedding search with: {rewritten_query}")
            query_embedding = generate_query_embedding(rewritten_query)
            embedding_results = self.retriever.search_similar(
                query_embedding,
                limit=10
            )

            # Merge results, avoid duplicates
            keyword_ids = {r["id"] for r in keyword_results}
            for r in embedding_results:
                if r["id"] not in keyword_ids:
                    # Lower threshold for embedding fallback
                    if r["relevance"] >= 0.55:
                        # Add match_score for consistency
                        r["match_score"] = r["relevance"] * 3  # Scale to comparable range
                        keyword_results.append(r)
                        print(f"  - [embedding] {r['relevance']:.2%}: {r['title'][:50]}...")

        # Prepare history for answer generation
        history_dicts = None
        if history:
            history_dicts = [
                {"role": h["role"], "content": h["content"]} for h in history
            ]

        # Step 5: Generate answer from sources
        if keyword_results:
            # Sort by match_score (keyword matches) + relevance (embedding)
            sorted_results = sorted(
                keyword_results,
                key=lambda x: x.get("match_score", 0) + x.get("relevance", 0) * 3,
                reverse=True
            )[:5]

            print(f"[DEBUG] Using {len(sorted_results)} sources for answer")

            answer = generate_answer(message, sorted_results, history_dicts)

            # Check if AI couldn't find answer in sources
            # If so, fall back to AI knowledge
            not_found_phrases = [
                "topilmadi",
                "mavjud emas",
                "ma'lumot yo'q",
                "javob yo'q",
            ]
            answer_lower = answer.lower()
            sources_insufficient = any(phrase in answer_lower for phrase in not_found_phrases)

            if sources_insufficient:
                print("[DEBUG] Sources insufficient, falling back to AI knowledge")
                fallback_result = generate_fallback_answer(message, history_dicts)
                return {
                    "answer": fallback_result["answer"],
                    "sources": [],
                    "source_type": "ai_knowledge",
                    "disclaimer": fallback_result["disclaimer"],
                }

            # Sources were helpful - return database answer
            sources = [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "relevance": round(
                        item.get("relevance", item.get("match_score", 0) / 6),
                        2
                    ),
                }
                for item in sorted_results
            ]

            return {
                "answer": answer,
                "sources": sources,
                "source_type": "database",
            }

        # Step 6: No sources at all - AI fallback with disclaimer
        print("[DEBUG] No sources found, using AI fallback")
        fallback_result = generate_fallback_answer(message, history_dicts)

        return {
            "answer": fallback_result["answer"],
            "sources": [],
            "source_type": "ai_knowledge",
            "disclaimer": fallback_result["disclaimer"],
        }
