-- Migration 003: Create Fatvo.uz Tables
-- Purpose: Add schema for fatvo.uz API scraper (categories and questions)
-- Date: 2025-12-15

-- ============================================================================
-- STEP 1: Create fatvo_categories table
-- ============================================================================

CREATE TABLE IF NOT EXISTS fatvo_categories (
  id SERIAL PRIMARY KEY,
  category_id VARCHAR(255) UNIQUE NOT NULL,  -- API ID: "ync20sch5716c6r"
  name_cyr VARCHAR(500),                     -- "Намоз"
  name_lat VARCHAR(500),                     -- "Namoz"
  created TIMESTAMP,                         -- From API
  updated TIMESTAMP,                         -- From API
  scraped_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fatvo_categories_category_id
  ON fatvo_categories(category_id);

RAISE NOTICE 'Created fatvo_categories table with index';

-- ============================================================================
-- STEP 2: Create fatvo_questions table
-- ============================================================================

CREATE TABLE IF NOT EXISTS fatvo_questions (
  id SERIAL PRIMARY KEY,
  question_id VARCHAR(255) UNIQUE NOT NULL,  -- API ID: "6173k88889w2y6r"
  qid INTEGER,                               -- Sequential number from API
  category_id VARCHAR(255),                  -- FK to fatvo_categories

  -- Bilingual titles
  title_cyr TEXT,
  title_lat TEXT,

  -- Bilingual questions
  question_cyr TEXT,
  question_lat TEXT,

  -- Bilingual answers
  answer_cyr TEXT,
  answer_lat TEXT,

  -- Metadata
  answered_by VARCHAR(255),                  -- User ID who answered
  answered_time TIMESTAMP,                   -- When answered
  status VARCHAR(50),                        -- 'answered', 'pending', etc.
  scope VARCHAR(50),                         -- 'public', 'private'
  views INTEGER DEFAULT 0,

  -- Timestamps from API
  created TIMESTAMP,
  updated TIMESTAMP,
  scraped_at TIMESTAMP DEFAULT NOW(),

  -- Session tracking (reuse existing table)
  session_id INTEGER REFERENCES scrape_sessions(id),

  -- Foreign key
  FOREIGN KEY (category_id) REFERENCES fatvo_categories(category_id) ON DELETE SET NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_fatvo_questions_category
  ON fatvo_questions(category_id);
CREATE INDEX IF NOT EXISTS idx_fatvo_questions_qid
  ON fatvo_questions(qid);
CREATE INDEX IF NOT EXISTS idx_fatvo_questions_question_id
  ON fatvo_questions(question_id);
CREATE INDEX IF NOT EXISTS idx_fatvo_questions_status
  ON fatvo_questions(status);
CREATE INDEX IF NOT EXISTS idx_fatvo_questions_views
  ON fatvo_questions(views);
CREATE INDEX IF NOT EXISTS idx_fatvo_questions_session
  ON fatvo_questions(session_id);

RAISE NOTICE 'Created fatvo_questions table with 6 indexes';

-- ============================================================================
-- STEP 3: Verification queries
-- ============================================================================

DO $$
DECLARE
    v_categories_exists BOOLEAN;
    v_questions_exists BOOLEAN;
    v_categories_indexes INTEGER;
    v_questions_indexes INTEGER;
BEGIN
    -- Check if tables exist
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'fatvo_categories'
    ) INTO v_categories_exists;

    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'fatvo_questions'
    ) INTO v_questions_exists;

    -- Count indexes
    SELECT COUNT(*) INTO v_categories_indexes
    FROM pg_indexes
    WHERE tablename = 'fatvo_categories';

    SELECT COUNT(*) INTO v_questions_indexes
    FROM pg_indexes
    WHERE tablename = 'fatvo_questions';

    RAISE NOTICE '';
    RAISE NOTICE '=== VERIFICATION RESULTS ===';
    RAISE NOTICE 'fatvo_categories table exists: %', v_categories_exists;
    RAISE NOTICE 'fatvo_categories indexes: %', v_categories_indexes;
    RAISE NOTICE 'fatvo_questions table exists: %', v_questions_exists;
    RAISE NOTICE 'fatvo_questions indexes: %', v_questions_indexes;
    RAISE NOTICE '';

    IF v_categories_exists AND v_questions_exists THEN
        RAISE NOTICE 'Migration 003 completed successfully!';
        RAISE NOTICE '';
        RAISE NOTICE 'Next steps:';
        RAISE NOTICE '1. Extend Database class (db.py) with fatvo methods';
        RAISE NOTICE '2. Create FatvoScraper class (src/app/fatvo/scraper.py)';
        RAISE NOTICE '3. Update docker-compose.yml to add fatvo_scraper service';
        RAISE NOTICE '4. Deploy and test';
    ELSE
        RAISE WARNING 'Migration may have failed - please check table creation';
    END IF;
END $$;

-- ============================================================================
-- Migration 003 complete!
-- ============================================================================
