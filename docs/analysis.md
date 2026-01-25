# AskAI System Analysis

**Date:** 2026-01-26

---

## 1. Architecture Overview

```
User Query
    │
    ▼
┌─────────────────────────────┐
│ 1. classify_message()       │  Conversational vs Question
└─────────────────────────────┘
    │ (if question)
    ▼
┌─────────────────────────────┐
│ 2. extract_search_keywords()│  AI extracts Cyrillic keywords
│    "mahsiga mash" →         │  + Islamic terminology
│    ["маҳси", "масҳ", ...]   │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 3. search_by_keywords()     │  PostgreSQL ILIKE
└─────────────────────────────┘
    │
    ├── ≥3 results → Use these
    │
    ▼ (<3 results)
┌─────────────────────────────┐
│ 4. embedding_search()       │  pgvector fallback
│    threshold: 0.55          │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 5. generate_answer()        │
│    ↓                        │
│ If "topilmadi" detected:    │
│    → AI fallback            │
└─────────────────────────────┘
```

---

## 2. Database Sources vs AI-Only

### 2.1 Comparison Table

| Factor | Database Sources | AI-Only |
|--------|------------------|---------|
| **Authority** | From islom.uz scholars - verifiable | "AI said so" - no accountability |
| **Local context** | Uzbekistan-specific, O'zMI references | Generic Islamic knowledge |
| **Consistency** | Same answer every time | Can vary between calls |
| **Traceability** | User can click source, read full fatwa | No way to verify |
| **Cost** | Free, instant DB query | API costs per query |
| **Trust** | "Scholars say..." | "AI thinks..." |
| **Coverage** | Limited to scraped content | Virtually unlimited |
| **Modern topics** | May be outdated/missing | Can reason about new topics |

### 2.2 When Database Excels

- Traditional fiqh questions (namoz, ro'za, zakot, haj)
- Questions with clear scholarly consensus
- Local/cultural context matters
- User wants verifiable source
- High-frequency common questions

### 2.3 When AI Excels

- Modern topics (crypto, technology, space)
- Hypothetical scenarios
- Synthesizing complex multi-part answers
- Step-by-step explanations
- No exact match in database

### 2.4 Conclusion

**Hybrid approach is optimal for religious Q&A:**

```
Database found + helpful    → Authoritative answer with sources (HIGH TRUST)
Database found + unhelpful  → Detect "topilmadi" → AI fallback
Database not found          → AI with disclaimer (MODERATE TRUST)
```

For religious matters, **sources matter**. Muslims asking fiqh questions want scholarly authority, not AI opinions. The database provides that trust layer.

---

## 3. Technical Implementation

### 3.1 Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `extract_search_keywords()` | gemini.py | AI extracts Cyrillic keywords with Islamic terminology |
| `search_by_keywords()` | search.py | PostgreSQL ILIKE multi-keyword search |
| `generate_answer()` | gemini.py | Answer from sources with Hanafi constraints |
| `generate_fallback_answer()` | gemini.py | AI knowledge with disclaimer |

### 3.2 Hanafi/Moturudi Constraints

Both `generate_answer()` and `generate_fallback_answer()` include:

```
MAZHAB VA AQIDA:
- Fiqh masalalarida Hanafiy mazhabni ustun qo'y (Imom Abu Hanifa ta'limoti)
- Aqida masalalarida Moturidiy yo'lini tut
- O'zbekiston musulmonlari an'analarini hurmat qil
- Agar manbalarda turli mazhablar fikri bo'lsa, Hanafiy mazhabni asosiy qilib ko'rsat
```

### 3.3 Fallback Detection

```python
not_found_phrases = [
    "topilmadi",
    "mavjud emas",
    "ma'lumot yo'q",
    "javob yo'q",
]
if any(phrase in answer.lower() for phrase in not_found_phrases):
    # Sources didn't help → trigger AI fallback
    return generate_fallback_answer(message)
```

### 3.4 Response Structure

```json
{
  "answer": "...",
  "sources": [
    {"id": 123, "title": "...", "relevance": 0.85}
  ],
  "source_type": "database" | "ai_knowledge" | "conversational",
  "disclaimer": "Bu javob sun'iy intellekt tomonidan..."
}
```

---

## 4. Islamic Terminology Handling

### 4.1 The Problem

Simple transliteration fails for Arabic-origin terms:

| Input | Simple Transliteration | Correct | Issue |
|-------|------------------------|---------|-------|
| mash | маш | масҳ | "sh" → "ш" but should be "сҳ" |
| mahsi | маҳси | маҳси | ✓ Works |
| vuzu | вузу | таҳорат | Need synonym |

### 4.2 The Solution

AI keyword extraction understands Islamic terminology:

```
"mash" → "масҳ" (not "маш")
"wudu" → "таҳорат" (synonym added)
"namoz" → "намоз" + related: "фарз", "суннат", "жамоат"
```

### 4.3 Terminology Mapping in Prompt

The `extract_search_keywords()` prompt includes:
- 30+ Islamic term mappings
- Latin → Cyrillic conversions
- Related terms and synonyms

---

## 5. Frontend Display

| Source Type | Display |
|-------------|---------|
| `database` | Answer + clickable sources list |
| `ai_knowledge` | Answer + yellow disclaimer banner |
| `conversational` | Simple response, no sources |

### Disclaimer Banner (ai_knowledge)
```
⚠️ Bu javob sun'iy intellekt tomonidan berildi.
Aniq fatvo uchun mahalliy imom yoki O'zbekiston
Musulmonlar Idorasiga murojaat qiling.
```

---

## 6. Strengths

1. **Hybrid approach** - Best of both worlds
2. **Hanafi-focused** - Consistent with Uzbek Islamic tradition
3. **Smart fallback** - Detects when sources don't help
4. **Transparent** - Users know source type
5. **Verifiable** - Database answers link to original
6. **Modern handling** - AI covers edge cases

## 7. Potential Improvements

- [ ] Track frequently asked questions that trigger AI fallback → add to database
- [ ] User feedback mechanism for answer quality
- [ ] Cache frequent queries
- [ ] Add more Islamic terminology to keyword extraction
- [ ] Consider multi-language support (Russian, English)
- [ ] Scholarly name recognition (Imom Buxoriy references)

---

## 8. Competitive Advantage

Generic AI chatbots (ChatGPT, etc.) can answer Islamic questions but lack:

1. **Local authority** - No islom.uz scholar backing
2. **Uzbek context** - Generic, not O'zbekiston-specific
3. **Madhab consistency** - May mix different schools
4. **Verifiability** - No source links
5. **Trust** - Users skeptical of AI for religious matters

AskAI's database sources provide the **authority and trust** that pure AI cannot.
