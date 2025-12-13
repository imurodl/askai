-- Initialize database schema for DinAI

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Track scraping sessions (for resuming and monitoring)
CREATE TABLE scrape_sessions (
  id SERIAL PRIMARY KEY,
  start_url TEXT NOT NULL,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  status VARCHAR(20) CHECK (status IN ('running', 'completed', 'failed')),
  pages_scraped INTEGER DEFAULT 0,
  last_scraped_url TEXT,
  errors TEXT
);

-- Store Q&A content
CREATE TABLE questions (
  id SERIAL PRIMARY KEY,
  session_id INTEGER REFERENCES scrape_sessions(id),
  url TEXT UNIQUE NOT NULL,
  question_title TEXT NOT NULL,
  question_text TEXT,
  answer TEXT NOT NULL,
  answer_author TEXT,
  category TEXT,
  published_date TEXT,
  scraped_at TIMESTAMP DEFAULT NOW(),
  metadata JSONB
);

-- Create indexes for better query performance
CREATE INDEX idx_questions_url ON questions(url);
CREATE INDEX idx_questions_session ON questions(session_id);
CREATE INDEX idx_scrape_sessions_status ON scrape_sessions(status);

-- Display successful initialization message
DO $$
BEGIN
    RAISE NOTICE 'DinAI database schema initialized successfully!';
END $$;
