# AskAI

RAG-powered Islamic Q&A chatbot for Uzbek Muslims using FastAPI, PostgreSQL/pgvector, React, and Google Gemini.

## Git Rules

- **NEVER** include "Co-Authored-By" lines in commit messages
- Use conventional commits (feat:, fix:, docs:, etc.)

## Working Style Preferences

- Be brief but don't sacrifice meaning or important details
- Think through implications before acting
- Use Docker for running services when available

## Architecture

```
User Query
    ↓
[1] classify_message() - conversational vs question
    ↓
[2] extract_search_keywords() - AI extracts Cyrillic keywords
    ↓
[3] search_by_keywords() - PostgreSQL ILIKE (fast, exact)
    ↓
[4] embedding_search() - pgvector fallback if <3 results
    ↓
[5] generate_answer() - from sources with Hanafi constraints
    ↓
[6] If "topilmadi" detected → generate_fallback_answer() with disclaimer
```

## Islamic Context

- **Madhab:** Hanafi (Imam Abu Hanifa)
- **Aqeedah:** Moturudi
- **Context:** Uzbekistan Muslims, O'zbekiston Musulmonlar Idorasi
- **Language:** Uzbek (Latin and Cyrillic)

## Key Files

### Backend (Python/FastAPI)
- `src/app/api/chat.py` - Main chat flow, keyword→embedding→fallback logic
- `src/app/api/search.py` - Keyword search with ILIKE
- `src/app/api/main.py` - FastAPI routes
- `src/app/rag/gemini.py` - AI functions (keyword extraction, answer generation, fallback)
- `src/app/rag/retriever.py` - pgvector similarity search
- `src/app/rag/embeddings.py` - Batch embedding generation

### Frontend (React/TypeScript)
- `web/src/pages/Chat.tsx` - Chat page
- `web/src/components/ChatMessage.tsx` - Message display with sources/disclaimer
- `web/src/api.ts` - API types and functions

### Config
- `docker-compose.yml` - Services configuration
- `.env` - Database and API keys

## Response Types

```typescript
{
  answer: string;
  sources: [{id, title, relevance}];
  source_type: "database" | "ai_knowledge" | "conversational";
  disclaimer?: string;  // Only for ai_knowledge
}
```

## Running Locally

```bash
# Backend
source .venv/bin/activate
uvicorn src.app.api.main:app --reload --port 8000

# Frontend
cd web && npm run dev
```

## Running with Docker

```bash
docker compose up -d
```

**Ports:**
- 8000 - API
- 5173 - Frontend (dev)
- 8080 - Adminer
- 5432 - PostgreSQL

## Database

- PostgreSQL with pgvector extension
- ~100k questions from islom.uz
- 768-dimensional embeddings (Gemini text-embedding-004)
- IVFFlat index for similarity search

## Documentation

- `docs/testing-results.md` - Test cases and results
- `docs/analysis.md` - Architecture and design decisions
