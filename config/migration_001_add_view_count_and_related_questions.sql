-- Migration: Add view_count and related_questions table
-- Run this migration to update the schema

-- Step 1: Add view_count to questions table
ALTER TABLE questions 
ADD COLUMN view_count INTEGER DEFAULT 0;

-- Step 2: Drop metadata column (no longer needed)
ALTER TABLE questions 
DROP COLUMN IF EXISTS metadata;

-- Step 3: Create related_questions table
CREATE TABLE IF NOT EXISTS related_questions (
  id SERIAL PRIMARY KEY,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  related_question_url TEXT NOT NULL,
  related_question_title TEXT NOT NULL,
  position INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Step 4: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_related_questions_question_id ON related_questions(question_id);
CREATE INDEX IF NOT EXISTS idx_related_questions_url ON related_questions(related_question_url);
CREATE INDEX IF NOT EXISTS idx_questions_view_count ON questions(view_count);

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Added view_count column to questions table';
    RAISE NOTICE 'Removed metadata column from questions table';
    RAISE NOTICE 'Created related_questions table';
END $$;
