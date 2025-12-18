"""Gemini API wrapper for embeddings and chat generation."""

import os
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Models
EMBEDDING_MODEL = "models/text-embedding-004"
CHAT_MODEL = "gemini-2.0-flash"


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a text using Gemini.

    Args:
        text: Text to embed

    Returns:
        List of 768 floats representing the embedding
    """
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


def generate_query_embedding(text: str) -> List[float]:
    """Generate embedding for a search query.

    Args:
        text: Query text to embed

    Returns:
        List of 768 floats representing the embedding
    """
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


def generate_answer(
    query: str,
    context: List[dict],
    history: Optional[List[dict]] = None,
) -> str:
    """Generate an answer using Gemini with RAG context.

    Args:
        query: User's question
        context: List of relevant Q&A from database
        history: Optional conversation history

    Returns:
        Generated answer string
    """
    # Build context string from retrieved Q&A
    context_parts = []
    for i, item in enumerate(context, 1):
        context_parts.append(
            f"[Manba {i}]\n"
            f"Savol: {item['title']}\n"
            f"Javob: {item['answer']}\n"
        )
    context_str = "\n---\n".join(context_parts)

    # System prompt
    system_prompt = """Sen islomiy savolarga javob beruvchi yordamchisan.
Sening vazifang foydalanuvchi savoliga berilgan manbalar asosida aniq va to'liq javob berish.

Qoidalar:
1. Faqat berilgan manbalar asosida javob ber
2. Agar manbalardan javob topilmasa, "Bu savol bo'yicha ma'lumot topilmadi" de
3. Javobni o'zbek tilida ber
4. Qisqa va aniq javob ber, lekin muhim ma'lumotlarni qoldirma
5. Manbalarga ishora qilma, shunchaki javob ber"""

    # Build messages
    messages = [{"role": "user", "parts": [system_prompt]}]

    # Add history if provided
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            messages.append({"role": role, "parts": [msg["content"]]})

    # Add current query with context
    user_message = f"""Manbalar:
{context_str}

Foydalanuvchi savoli: {query}"""

    messages.append({"role": "user", "parts": [user_message]})

    # Generate response
    model = genai.GenerativeModel(CHAT_MODEL)
    chat = model.start_chat(history=messages[:-1])
    response = chat.send_message(messages[-1]["parts"][0])

    return response.text
