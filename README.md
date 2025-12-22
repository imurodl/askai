# AskAI

A RAG-powered AI chatbot for Islamic Q&A content.

## Local Development

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL with pgvector

### Setup

```bash
# Install backend dependencies
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Install frontend dependencies
cd web && npm install && cd ..
```

### Environment

Create `.env` file:

```
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=islambot
DB_USER=your-user
DB_PASSWORD=your-password
GEMINI_API_KEY=your-gemini-key
```

### Run

```bash
# Terminal 1: Backend
.venv/bin/python -m uvicorn src.app.api.main:app --reload --port 8000

# Terminal 2: Frontend
cd web && npm run dev
```

Open http://localhost:5173

## Tech Stack

- **Backend**: FastAPI, PostgreSQL + pgvector, Gemini API
- **Frontend**: React, Vite, Tailwind CSS
