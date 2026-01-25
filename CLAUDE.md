# AskAI

RAG-powered Islamic Q&A chatbot using FastAPI, PostgreSQL/pgvector, React, and Google Gemini.

## Working Style Preferences

- Be brief but don't sacrifice meaning or important details
- Use Docker for running services (not direct npm/python)
- Think through implications before acting (e.g., port accessibility, firewall)

## Git Rules

- No "Co-Authored-By" lines in commits

## Key Paths

- **API:** `src/app/api/`
- **RAG:** `src/app/rag/`
- **Frontend:** `web/`
- **Config:** `docker-compose.yml`, `.env`

## Running the Project

```bash
docker compose up -d
```

**Ports:**
- 8000 - API
- 8080 - Adminer
- 5432 - PostgreSQL
