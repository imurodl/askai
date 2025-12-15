-- Migration 002: Migrate to Many-to-Many Related Questions Structure
-- Purpose: Deduplicate related questions by using self-referencing many-to-many relationship
-- Date: 2025-12-15

-- ============================================================================
-- STEP 1: Add new column to questions table
-- ============================================================================

ALTER TABLE questions
ADD COLUMN IF NOT EXISTS is_fully_scraped BOOLEAN DEFAULT true;

-- Update existing questions to be marked as fully scraped
UPDATE questions SET is_fully_scraped = true WHERE is_fully_scraped IS NULL;

RAISE NOTICE 'Added is_fully_scraped column to questions table';

-- ============================================================================
-- STEP 2: Create question_relationships junction table
-- ============================================================================

CREATE TABLE IF NOT EXISTS question_relationships (
  id SERIAL PRIMARY KEY,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  related_question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  position INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),

  -- Ensure no duplicate relationships
  UNIQUE(question_id, related_question_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_question_relationships_question
  ON question_relationships(question_id);

CREATE INDEX IF NOT EXISTS idx_question_relationships_related
  ON question_relationships(related_question_id);

CREATE INDEX IF NOT EXISTS idx_questions_fully_scraped
  ON questions(is_fully_scraped);

RAISE NOTICE 'Created question_relationships junction table with indexes';

-- ============================================================================
-- STEP 3: Migrate existing data from related_questions table
-- ============================================================================

DO $$
DECLARE
    v_related_questions_count INTEGER;
    v_unique_urls_count INTEGER;
    v_new_placeholders_count INTEGER;
    v_relationships_count INTEGER;
BEGIN
    -- Check if old table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'related_questions') THEN

        -- Get counts for reporting
        SELECT COUNT(*) INTO v_related_questions_count FROM related_questions;
        SELECT COUNT(DISTINCT related_question_url) INTO v_unique_urls_count FROM related_questions;

        RAISE NOTICE 'Starting migration: % related_questions entries, % unique URLs',
            v_related_questions_count, v_unique_urls_count;

        -- Step 3A: Insert placeholder questions for unscraped related URLs
        INSERT INTO questions (url, question_title, question_text, answer, is_fully_scraped, session_id, answer_author, category, published_date, view_count)
        SELECT DISTINCT
            rq.related_question_url as url,
            rq.related_question_title as question_title,
            '' as question_text,
            '' as answer,
            false as is_fully_scraped,
            1 as session_id,  -- Dummy session_id for placeholders
            NULL as answer_author,
            NULL as category,
            NULL as published_date,
            0 as view_count
        FROM related_questions rq
        WHERE NOT EXISTS (
            SELECT 1 FROM questions q WHERE q.url = rq.related_question_url
        )
        ON CONFLICT (url) DO NOTHING;

        GET DIAGNOSTICS v_new_placeholders_count = ROW_COUNT;
        RAISE NOTICE 'Created % placeholder questions', v_new_placeholders_count;

        -- Step 3B: Populate junction table with relationships
        INSERT INTO question_relationships (question_id, related_question_id, position)
        SELECT DISTINCT
            rq.question_id,
            q.id as related_question_id,
            rq.position
        FROM related_questions rq
        JOIN questions q ON q.url = rq.related_question_url
        ON CONFLICT (question_id, related_question_id) DO NOTHING;

        GET DIAGNOSTICS v_relationships_count = ROW_COUNT;
        RAISE NOTICE 'Created % relationships in junction table', v_relationships_count;

        -- Step 3C: Backup old table (don't drop it)
        ALTER TABLE related_questions RENAME TO related_questions_backup;

        RAISE NOTICE 'Renamed related_questions to related_questions_backup';
        RAISE NOTICE 'Migration completed successfully!';
        RAISE NOTICE 'Summary:';
        RAISE NOTICE '  - Original entries: %', v_related_questions_count;
        RAISE NOTICE '  - Unique URLs: %', v_unique_urls_count;
        RAISE NOTICE '  - New placeholders created: %', v_new_placeholders_count;
        RAISE NOTICE '  - Relationships migrated: %', v_relationships_count;

    ELSE
        RAISE NOTICE 'related_questions table not found - skipping migration';
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Verification queries
-- ============================================================================

DO $$
DECLARE
    v_total_questions INTEGER;
    v_fully_scraped INTEGER;
    v_placeholders INTEGER;
    v_relationships INTEGER;
    v_orphaned INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total_questions FROM questions;
    SELECT COUNT(*) INTO v_fully_scraped FROM questions WHERE is_fully_scraped = true;
    SELECT COUNT(*) INTO v_placeholders FROM questions WHERE is_fully_scraped = false;
    SELECT COUNT(*) INTO v_relationships FROM question_relationships;

    SELECT COUNT(*) INTO v_orphaned
    FROM question_relationships qr
    WHERE NOT EXISTS (SELECT 1 FROM questions q WHERE q.id = qr.related_question_id);

    RAISE NOTICE '';
    RAISE NOTICE '=== VERIFICATION RESULTS ===';
    RAISE NOTICE 'Total questions: %', v_total_questions;
    RAISE NOTICE 'Fully scraped: %', v_fully_scraped;
    RAISE NOTICE 'Placeholders: %', v_placeholders;
    RAISE NOTICE 'Relationships: %', v_relationships;
    RAISE NOTICE 'Orphaned relationships: % (should be 0)', v_orphaned;
    RAISE NOTICE '';

    IF v_orphaned > 0 THEN
        RAISE WARNING 'Found orphaned relationships! Please investigate.';
    ELSE
        RAISE NOTICE 'No orphaned relationships - migration integrity verified!';
    END IF;
END $$;

-- ============================================================================
-- Migration complete!
-- ============================================================================

RAISE NOTICE '';
RAISE NOTICE '=== MIGRATION 002 COMPLETED ===';
RAISE NOTICE 'Next steps:';
RAISE NOTICE '1. Update db.py to use new structure';
RAISE NOTICE '2. Test the scraper';
RAISE NOTICE '3. If everything works, drop related_questions_backup table';
RAISE NOTICE '';
