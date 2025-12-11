# DinAI - RAG AI Chatbot Project Plan

## Project Overview

DinAI is a Retrieval-Augmented Generation (RAG) AI chatbot that provides intelligent responses based on scraped web content stored in a vector database.

---

## Phase 1: Web Scraper Development

### 1.1 Setup & Dependencies

- **Technology Stack**:

  - Python 3.11+ (or 3.12)
  - **uv** for Python dependency management and virtual environments
  - Beautiful Soup 4 / Scrapy for web scraping
  - Selenium (for dynamic content if needed)
  - **PostgreSQL with pgvector extension** (unified structured + vector database)
  - Docker & Docker Compose for PostgreSQL containerization
  - LangChain for document processing
  - FastAPI for API endpoints
  - ruff for linting and formatting
  - pytest for testing

- **Initial Setup**:
  - Initialize uv project (`uv init`)
  - Create virtual environment with uv
  - Set up Docker Compose for PostgreSQL
  - Install required dependencies via uv
  - Configure environment variables (.env file)
  - Set up project structure

### 1.2 Web Scraper Core Features

#### Target Website: savollar.islom.uz
- **Starting URL**: `https://savollar.islom.uz/s/2`
- **Crawl Strategy**: Follow "next question" links sequentially
- **Rate Limiting**: 1 request per second (respectful scraping)
- **Estimated Volume**: Thousands of Q&A pages
- **Reference HTML**: See `response-example.html` for actual page structure

#### URL Management
- Start from initial URL (e.g., `/s/2`)
- Extract "next question" link from HTML: 
  ```html
  <div class='col-lg-6'>
    <a href='/s/3'>  <!-- Extract this href -->
  ```
- Follow chain until no "next question" link exists
- Implement URL validation and deduplication
- Track visited URLs to avoid loops
- Support for robots.txt compliance

#### Content Extraction (from savollar.islom.uz)
*Reference: See `response-example.html` for complete HTML structure*

- **Question Title**: Extract from `<h1>` tag
  ```html
  <h1>Инсон аъзоларидан бири кесиб ташланса, уни нима қилиш лозим?</h1>
  ```
- **Question Text**: Extract from `<div class='text_in_question'>`
- **Answer**: Extract from `<div class='answer_in_question'>`
- **Metadata**: 
  - Date and time (from `<div class='info_quesiton'>`)
  - Author/Source (e.g., "eski savollar")
  - Category (from breadcrumb: `<nav aria-label="breadcrumb">`)
  - View count
- **Next Link**: Extract href from `<a href='/s/X'>` inside `<div class='col-lg-6'>` with `next_question_b` class
  ```html
  <div class='col-lg-6'>
    <a href='/s/3'>  <!-- This is the next URL -->
  ```
- Clean and normalize Uzbek text (Cyrillic encoding)
- Handle HTML entities and special characters

#### Rate Limiting & Respectful Scraping
- **Fixed delay**: 1 second between requests (configurable)
- **Exponential backoff**: If 429 (Too Many Requests) received
- **User-Agent**: Identify as DinAI bot with contact info
- **Respect robots.txt**: Check before starting
- **Time-based throttling**: Avoid peak hours if needed
- **Maximum retries**: 3 attempts per URL

#### Error Handling
- Implement retry logic with exponential backoff
- Handle HTTP errors (404, 500, 503)
- Handle network timeouts
- Log failed URLs with error details for manual review
- Continue crawling even if individual pages fail
- Graceful shutdown (save progress on interrupt)

### 1.3 Data Processing Pipeline

- **Text Preprocessing**:

  - Remove HTML tags and special characters
  - Normalize whitespace and encoding
  - Split content into manageable chunks (for embeddings)
  - Maintain document structure and hierarchy

- **Metadata Enrichment**:
  - Extract keywords and entities
  - Calculate content hash for deduplication
  - Store source URL and scrape timestamp
  - Track content version/updates

### 1.4 Database Schema Design

#### PostgreSQL Database Schema

**documents table**

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT UNIQUE NOT NULL,
  title TEXT,
  content TEXT,
  content_hash TEXT,
  metadata JSONB,
  scraped_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  status VARCHAR(20) CHECK (status IN ('active', 'outdated', 'error'))
);
```

**scrape_jobs table**

```sql
CREATE TABLE scrape_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  target_url TEXT NOT NULL,
  status VARCHAR(20) CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  pages_scraped INTEGER DEFAULT 0,
  errors JSONB
);
```

**document_chunks table (with pgvector)**

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  chunk_text TEXT NOT NULL,
  embedding vector(1536),  -- dimension depends on embedding model
  chunk_index INTEGER,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

### 1.5 Scraper Configuration

- **Configurable Parameters**:
  - Starting URL (default: `https://savollar.islom.uz/s/2`)
  - Crawl delay / rate limit (default: 1 second)
  - Max pages to scrape (optional limit for testing)
  - User-agent string (e.g., "DinAI-Bot/1.0 (+contact@email.com)")
  - Request timeout values (default: 30 seconds)
  - Retry attempts (default: 3)

### 1.6 Monitoring & Logging

- Implement structured logging (Python logging module)
- Track scraping metrics:
  - Pages scraped per minute
  - Success/failure rate
  - Current position in chain (e.g., /s/1234)
  - Estimated time remaining
- Progress persistence (save state for resumption)
- Alert system for critical failures
- Simple CLI dashboard showing real-time progress

### 1.7 Scraper Workflow (savollar.islom.uz)

**Sequential Crawling Process:**
```
1. Start: https://savollar.islom.uz/s/2
2. Fetch page (wait 1 second before request)
3. Parse HTML and extract:
   - Question title (<h1>)
   - Question text (<div class='text_in_question'>)
   - Answer (<div class='answer_in_question'>)
   - Metadata (date, author, category from breadcrumb)
   - Next link (<a href='/s/X'> in next_question_b div)
4. Save to PostgreSQL
5. Check if next link exists:
   - YES: Add to queue, go to step 2
   - NO: End of chain, log completion
6. Handle errors gracefully, continue with next URL
```

**Key Implementation Details:**
- Use Beautiful Soup for HTML parsing
- Store next question link from: `<div class='col-lg-6'><a href='/s/3'>`
- Detect end of chain when next link div is missing or empty
- Maintain visited URLs set to prevent infinite loops
- Save progress periodically (every 100 pages)

---

## Phase 2: RAG System Implementation (Future)

### 2.1 Embedding Generation

- Choose embedding model (OpenAI text-embedding-3-small, Cohere, or local models)
- Generate embeddings for scraped content chunks
- Store embeddings in PostgreSQL using pgvector
- Implement batch processing for efficiency
- Match embedding dimensions to model output (e.g., 1536 for OpenAI)

### 2.2 Vector Search Setup

- Configure pgvector indexes (IVFFlat or HNSW)
- Define similarity metrics (cosine, L2, inner product)
- Implement efficient upsert operations
- Optimize search with appropriate index parameters

### 2.3 Retrieval System

- Implement semantic search
- Hybrid search (keyword + semantic)
- Re-ranking mechanisms
- Context window management

### 2.4 LLM Integration

- Choose LLM provider (OpenAI, Anthropic, local models)
- Implement prompt engineering
- Context injection from retrieved documents
- Response generation pipeline

---

## Phase 3: Chatbot Interface (Future)

### 3.1 Backend API

- RESTful API / GraphQL endpoints
- WebSocket for real-time chat
- Session management
- Rate limiting and authentication

### 3.2 Frontend Development

- Web interface (React/Vue/Svelte)
- Chat UI components
- Source citation display
- Conversation history

### 3.3 Features

- Multi-turn conversations
- Source attribution
- Feedback collection
- Export conversation history

---

## Phase 4: Maintenance & Updates (Future)

### 4.1 Content Refresh Strategy

- Scheduled re-scraping of sources
- Detect content changes
- Update embeddings for modified content
- Archive outdated content

### 4.2 Performance Optimization

- Caching strategies
- Query optimization
- Load balancing
- Cost optimization for API calls

### 4.3 Quality Assurance

- Response quality metrics
- A/B testing different retrieval strategies
- User satisfaction tracking
- Continuous improvement pipeline

---

## Immediate Next Steps

1. **Week 1-2: Scraper Foundation**

   - Initialize uv project and create virtual environment
   - Set up Docker Compose for PostgreSQL with pgvector
   - Create project structure (src/, tests/, config/)
   - Install core dependencies via uv (beautifulsoup4, psycopg3, etc.)
   - Implement basic web scraper with Beautiful Soup
   - Create database schema (documents, scrape_jobs, document_chunks tables)
   - Build URL queue management system

2. **Week 3-4: Advanced Scraping**

   - Add Selenium for dynamic content
   - Implement error handling and retry logic
   - Add content processing and chunking pipeline
   - Build monitoring and logging system

3. **Week 5-6: Embeddings & Testing**
   - Integrate embedding model (OpenAI or open-source)
   - Generate and store embeddings in PostgreSQL using pgvector
   - Create vector similarity search functions
   - Comprehensive testing with real websites
   - Documentation and configuration guides

---

## Technology Recommendations

### Web Scraper Stack

- **Primary**: Python with Beautiful Soup 4
- **Dynamic Content**: Selenium + ChromeDriver
- **Alternative**: Scrapy (for large-scale scraping)
- **API Wrapper**: FastAPI for scraper controls

### Database Stack (Finalized)

- **Database**: PostgreSQL 15+ with pgvector extension
  - **Why**: Unified solution for both structured data and vector embeddings
  - **Benefits**: Single database to manage, JSONB for flexible metadata, strong ACID compliance
  - **Vectors**: pgvector handles up to millions of vectors efficiently
  - **Scaling**: IVFFlat and HNSW indexes for fast similarity search

### Development Environment

- **Python**: 3.11+ managed with uv
- **IDE**: VS Code with Python, PostgreSQL extensions
- **Database**: PostgreSQL in Docker container
- **Dependency Management**: uv (fast, modern Python package manager)
- **Environment Variables**: .env with python-dotenv

### Deployment

- Docker containers for application
- Docker Compose for local development
- Scheduled jobs with cron/Celery
- Cloud platforms: AWS/GCP/Azure or VPS

---

## Success Metrics

### Phase 1 (Web Scraper)

- Successfully scrape and store 1000+ pages
- Error rate < 5%
- Processing speed > 10 pages/minute
- Zero duplicate content in database

### Overall Project

- Response accuracy > 85%
- Average response time < 3 seconds
- User satisfaction score > 4/5
- System uptime > 99%

---

## Notes & Considerations

- **Legal Compliance**: Always check robots.txt and terms of service
- **Ethical Scraping**: Implement rate limiting to avoid overwhelming servers
- **Data Privacy**: Handle sensitive information appropriately
- **Scalability**: Design with horizontal scaling in mind
- **Cost Management**: Monitor API usage and database costs

---

**Project Start Date**: December 11, 2025  
**Current Phase**: Phase 1 - Web Scraper Development  
**Status**: Planning Complete, Ready for Implementation
