-- Migration 005: Add session tracking and chat history tables
-- Purpose: Track user sessions and persist chat messages
-- Date: 2026-01-27

-- ============================================================================
-- STEP 1: Create sessions table
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    user_agent TEXT,
    device_type VARCHAR(20),
    language VARCHAR(10),
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active_at);
CREATE INDEX IF NOT EXISTS idx_sessions_device_type ON sessions(device_type);

-- ============================================================================
-- STEP 2: Create chat table
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    sources JSONB DEFAULT '[]',
    keywords TEXT[] DEFAULT '{}',
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_session ON chat(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_source_type ON chat(source_type);

-- ============================================================================
-- STEP 3: Verification
-- ============================================================================

DO $$
DECLARE
    v_sessions_exists BOOLEAN;
    v_chat_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'sessions'
    ) INTO v_sessions_exists;

    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'chat'
    ) INTO v_chat_exists;

    RAISE NOTICE '';
    RAISE NOTICE '=== VERIFICATION RESULTS ===';
    RAISE NOTICE 'sessions table exists: %', v_sessions_exists;
    RAISE NOTICE 'chat table exists: %', v_chat_exists;
    RAISE NOTICE '';

    IF v_sessions_exists AND v_chat_exists THEN
        RAISE NOTICE 'Migration 005 completed successfully!';
    ELSE
        RAISE WARNING 'Migration may have failed - please check manually';
    END IF;
END $$;
