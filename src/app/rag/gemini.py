"""Gemini API wrapper for embeddings and chat generation."""

import os
import json
from typing import List, Optional, Dict, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Models
EMBEDDING_MODEL = "text-embedding-004"
CHAT_MODEL = "gemini-2.0-flash"


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a text using Gemini.

    Args:
        text: Text to embed

    Returns:
        List of 768 floats representing the embedding
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return result.embeddings[0].values


def generate_embedding_with_key(text: str, api_key: str) -> List[float]:
    """Generate embedding using a specific API key.

    Args:
        text: Text to embed
        api_key: Google API key to use

    Returns:
        List of 768 floats representing the embedding
    """
    custom_client = genai.Client(api_key=api_key)
    result = custom_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return result.embeddings[0].values


def generate_query_embedding(text: str) -> List[float]:
    """Generate embedding for a search query.

    Args:
        text: Query text to embed

    Returns:
        List of 768 floats representing the embedding
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def extract_search_keywords(query: str) -> Dict[str, Any]:
    """Extract proper Uzbek Cyrillic keywords from user query using AI.

    AI understands Islamic terminology and can:
    - Convert Latin to proper Cyrillic (understanding Arabic-origin terms)
    - Add related terms and synonyms
    - Understand context-specific meanings

    Args:
        query: User's question (in Latin or Cyrillic)

    Returns:
        dict with:
            - primary_keywords: List[str] - main search terms
            - related_keywords: List[str] - synonyms and related terms
            - rewritten_query: str - full query in Cyrillic for embeddings
    """
    prompt = f"""Sen islomiy terminologiya bo'yicha mutaxassissan. Foydalanuvchi savolidan qidiruv uchun kalit so'zlarni ajratib ber.

MUHIM QOIDALAR:
1. Barcha kalit so'zlarni KIRILL alifbosida yoz
2. Islomiy terminlarni TO'G'RI yoz (arabcha asl shaklga yaqin):
   - "mash" yoki "masx" → "масҳ" (таҳоратда оёққа масҳ тортиш)
   - "mahsi" → "маҳси" (махсус пайпоқ)
   - "vuzu" yoki "wudu" → "таҳорат"
   - "namoz" yoki "salat" → "намоз"
   - "roza" yoki "sawm" → "рўза"
   - "zakot" → "закот"
   - "haj" → "ҳаж"
   - "nikoh" → "никоҳ"
   - "talaq" → "талоқ"
   - "halol" → "ҳалол"
   - "harom" → "ҳаром"
   - "farz" → "фарз"
   - "sunnat" → "суннат"
   - "janoza" → "жаноза"
   - "ghusl" yoki "g'usl" → "ғусл"
   - "sajda" → "сажда"
   - "ruku" → "рукуъ"
   - "qibla" → "қибла"
   - "duo" yoki "dua" → "дуо"
   - "zikr" → "зикр"
   - "hadis" → "ҳадис"
   - "fatvo" → "фатво"
   - "ibodat" → "ибодат"
   - "tahorat" → "таҳорат"
   - "istinjo" → "истинжо"
   - "tayammum" → "таяммум"
   - "qazo" → "қазо"
   - "juma" → "жума"
   - "hayit" → "ҳайит"
   - "iftor" → "ифтор"
   - "saharlik" → "саҳарлик"
   - "mehr" → "меҳр"
   - "aqiqa" → "ақиқа"
3. Tegishli so'zlarni ham qo'sh (sinonimlar, bog'liq tushunchalar)
4. Savolni to'liq Kirill alifbosida qayta yoz

Foydalanuvchi savoli: "{query}"

Faqat JSON formatida javob ber, boshqa hech narsa yozma:
{{"primary_keywords": ["asosiy", "kalit", "sozlar"], "related_keywords": ["tegishli", "sozlar"], "rewritten_query": "Savol kirill alifbosida"}}"""

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
        ),
    )

    try:
        # Parse JSON response
        result_text = response.text.strip()
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            result_text = result_text.rsplit("```", 1)[0]
        result = json.loads(result_text)
        return {
            "primary_keywords": result.get("primary_keywords", []),
            "related_keywords": result.get("related_keywords", []),
            "rewritten_query": result.get("rewritten_query", query),
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[WARNING] Failed to parse keyword extraction response: {e}")
        # Fallback: return original query as keyword
        return {
            "primary_keywords": [query],
            "related_keywords": [],
            "rewritten_query": query,
        }


def classify_message(message: str) -> bool:
    """Classify if a message is a question that needs RAG search.

    Args:
        message: User's message

    Returns:
        True if message needs RAG search, False if conversational
    """
    prompt = f"""Foydalanuvchi xabarini tahlil qil. Bu islomiy savol yoki ma'lumot so'rayotgan savolmi?

Xabar: "{message}"

Agar bu:
- Islomiy savol (namoz, ro'za, zakot, haj, nikoh, halol-harom va h.k.)
- Ma'lumot so'rayotgan savol
- Diniy masala haqida so'rov
bo'lsa "SAVOL" deb javob ber.

Agar bu:
- Salomlashish (salom, assalomu alaykum)
- Xayrlashish (xo'sh, hayr, ko'rishguncha)
- Oddiy suhbat (rahmat, ok, ha, yo'q, yaxshi)
- Savol emas, shunchaki gap
bo'lsa "SUHBAT" deb javob ber.

Faqat bitta so'z bilan javob ber: SAVOL yoki SUHBAT"""

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
        ),
    )

    result = response.text.strip().upper()
    return "SAVOL" in result


def generate_conversational_response(message: str) -> str:
    """Generate a conversational response without RAG.

    Args:
        message: User's conversational message

    Returns:
        Appropriate conversational response
    """
    prompt = f"""Sen do'stona yordamchisan. Foydalanuvchi senga salomlashdi yoki oddiy gap aytdi.
Unga qisqa va do'stona javob ber. O'zbek tilida javob ber.

Foydalanuvchi: {message}

Qisqa javob ber (1-2 jumla). Agar salomlashsa, salomlash va yordam taklif qil. Agar xayrlashsa, xayrlashtir."""

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
        ),
    )

    return response.text.strip()


def generate_conversational_response_with_history(
    message: str,
    history: List[dict],
) -> str:
    """Generate conversational response with context from history.

    For messages like "rahmat", "qisqartir", etc. that need
    history context but are not questions needing AI knowledge disclaimer.

    Args:
        message: User's conversational message
        history: Conversation history

    Returns:
        Conversational response without disclaimer
    """
    system_prompt = """Sen do'stona yordamchisan. Foydalanuvchi oldingi suhbat davomida
so'rov yoki izoh qilmoqda. Unga qisqa va do'stona javob ber. O'zbek tilida javob ber.

Agar foydalanuvchi:
- "rahmat", "tashakkur" desa - minnatdorchilik qabul qil
- "qisqartir", "qisqaroq" desa - oldingi javobni qisqartir
- "batafsil", "ko'proq" desa - oldingi javobni kengaytir
- salomlashsa - salomlash
- xayrlashsa - xayrlashtir"""

    # Build contents with history
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=msg["content"])])
        )
    contents.append(
        types.Content(role="user", parts=[types.Part(text=message)])
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
        ),
    )

    return response.text.strip()


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
            f"[Manba {i}]\n" f"Savol: {item['title']}\n" f"Javob: {item['answer']}\n"
        )
    context_str = "\n---\n".join(context_parts)

    # System prompt
    system_prompt = """Sen Hanafiy mazhabiga asoslangan islomiy savol-javob yordamchisisan.
Sening vazifang foydalanuvchi savoliga berilgan manbalar asosida aniq va to'liq javob berish.

MAZHAB VA AQIDA:
- Fiqh masalalarida Hanafiy mazhabni ustun qo'y (Imom Abu Hanifa ta'limoti)
- Aqida masalalarida Moturidiy yo'lini tut
- O'zbekiston musulmonlari an'analarini hurmat qil
- Agar manbalarda turli mazhablar fikri bo'lsa, Hanafiy mazhabni asosiy qilib ko'rsat

JAVOB QOIDALARI:
1. Faqat berilgan manbalar asosida javob ber
2. Agar manbalardan javob topilmasa, "Bu savol bo'yicha ma'lumot topilmadi" deb ayt
3. Javobni o'zbek tilida, sodda va tushunarli qilib ber
4. Qisqa va aniq javob ber, lekin muhim ma'lumotlarni qoldirma
5. Manbalarga ishora qilma, shunchaki javob ber
6. Hadis yoki oyat keltirganingda imkon qadar manbasini ayt"""

    # Build user message with context
    user_message = f"""Manbalar:
{context_str}

Foydalanuvchi savoli: {query}"""

    # Build contents for the chat
    contents = []

    # Add history if provided
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )

    # Add current message
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    # Generate response
    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        ),
    )

    return response.text


def generate_fallback_answer(
    query: str,
    history: Optional[List[dict]] = None,
) -> Dict[str, str]:
    """Generate AI answer when no database sources found.

    Constrained to:
    - Hanafi madhab (fiqh)
    - Moturudi aqeedah (theology)
    - Uzbek Islamic context

    Args:
        query: User's question
        history: Conversation history

    Returns:
        dict with:
            - answer: str - AI-generated answer
            - disclaimer: str - standard disclaimer in Uzbek
    """
    system_prompt = """Sen Hanafiy mazhabiga asoslangan islomiy bilim yordamchisisan.

MUHIM CHEKLOVLAR:
1. Faqat Hanafiy mazhab bo'yicha javob ber (Imom Abu Hanifa ta'limoti asosida)
2. Aqida masalalarida Moturidiy yo'lini tut (Imom Moturidiy ta'limoti)
3. O'zbek musulmonlari an'analari va amaliyotini hurmat qil
4. Agar boshqa mazhablarning fikri farqli bo'lsa, Hanafiy mazhabni ustun qo'y
5. Bahsli masalalarda "mahalliy olimlarimizga murojaat qiling" deb ayt

MUMKIN BO'LMAGAN JAVOBLAR (bu mavzularda faqat umumiy ma'lumot ber):
- Fatvo chiqarish
- Nikoh, taloq haqida aniq hukmlar berish
- Halol-harom masalalarida qat'iy hukm chiqarish
- Meros taqsimoti haqida aniq hisob-kitob
Bu masalalar uchun faqat umumiy ma'lumot ber va O'zbekiston Musulmonlar Idorasiga yoki mahalliy imomga murojaat qilishni tavsiya et.

JAVOB FORMATI:
- Qisqa va aniq javob ber
- Hadis yoki oyat keltirganingda manbasini ayt (masalan: Buxoriy rivoyati, Niso surasi 4-oyat)
- Murakkab masalalarda bosqichma-bosqich tushuntir
- O'zbek tilida sof va tushunarli yoz"""

    # Build contents
    contents = []

    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )

    contents.append(
        types.Content(role="user", parts=[types.Part(text=query)])
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
        ),
    )

    disclaimer = "Bu javob sun'iy intellekt tomonidan berildi. Aniq fatvo uchun mahalliy imom yoki O'zbekiston Musulmonlar Idorasiga murojaat qiling."

    return {
        "answer": response.text,
        "disclaimer": disclaimer,
    }
