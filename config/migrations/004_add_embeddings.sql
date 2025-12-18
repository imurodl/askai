-- Migration 004: Add embeddings column for RAG
-- Purpose: Store vector embeddings for semantic search
-- Date: 2025-12-18

-- ============================================================================
-- STEP 1: Add embedding column to questions table
-- ============================================================================

-- Using 768 dimensions (Gemini text-embedding-004 output size)
ALTER TABLE questions ADD COLUMN IF NOT EXISTS embedding vector(768);

RAISE NOTICE 'Added embedding column to questions table';

-- ============================================================================
-- STEP 2: Create vector similarity index
-- ============================================================================

-- IVFFlat index for approximate nearest neighbor search
-- lists = 100 is good for ~10k vectors, adjust if dataset grows significantly
CREATE INDEX IF NOT EXISTS idx_questions_embedding
  ON questions USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

RAISE NOTICE 'Created IVFFlat index for vector similarity search';

-- ============================================================================
-- STEP 3: Verification
-- ============================================================================

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_index_exists BOOLEAN;
BEGIN
    -- Check if column exists
    SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'questions' AND column_name = 'embedding'
    ) INTO v_column_exists;

    -- Check if index exists
    SELECT EXISTS (
        SELECT FROM pg_indexes
        WHERE tablename = 'questions' AND indexname = 'idx_questions_embedding'
    ) INTO v_index_exists;

    RAISE NOTICE '';
    RAISE NOTICE '=== VERIFICATION RESULTS ===';
    RAISE NOTICE 'embedding column exists: %', v_column_exists;
    RAISE NOTICE 'vector index exists: %', v_index_exists;
    RAISE NOTICE '';

    IF v_column_exists AND v_index_exists THEN
        RAISE NOTICE 'Migration 004 completed successfully!';
        RAISE NOTICE '';
        RAISE NOTICE 'Next steps:';
        RAISE NOTICE '1. Run embedding generation script to populate vectors';
        RAISE NOTICE '2. Implement RAG pipeline with Gemini API';
    ELSE
        RAISE WARNING 'Migration may have failed - please check manually';
    END IF;
END $$;
