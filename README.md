# AskAI

A RAG-powered AI chatbot for Islamic Q&A content. Scrapes public fatwa data, stores it in PostgreSQL with vector embeddings, and provides semantic search capabilities.

**Note**: This project is being developed for personal use.

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Running the Project

1. **Clone the repository**

```bash
git clone https://github.com/imurodl/askai.git
cd askai
```

2. **Create environment file**

```bash
cat > .env << EOF
# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=askai
DB_USER=user
DB_PASSWORD=password

# Scraper Configuration
START_URL=https://your-source-url.com/start
CRAWL_DELAY=1.0
MAX_PAGES=0
REQUEST_TIMEOUT=30
MAX_RETRIES=3
USER_AGENT=AskAI-Bot/1.0
EOF
```

3. **Start the services**

```bash
docker-compose up -d
```

4. **View logs**

```bash
docker logs askai_scraper -f
```

5. **Check database**

```bash
docker exec -it askai_postgres psql -U askai_user -d askai -c "SELECT COUNT(*) FROM questions;"
```

### Stop the services

```bash
docker-compose down
```

## Tech Stack

- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- Beautiful Soup 4, requests
- PostgreSQL 15+ with pgvector
- Docker, Docker Compose

## Project Status

**Phase 1**: Web scraper with rate limiting and error handling ✅  
**Phase 2**: RAG system with embeddings and vector search (planned)  
**Phase 3**: Chatbot interface (planned)
