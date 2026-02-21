-- Migration 001: Shared schema for both Version A (LiveKit) and Version B (OpenAI Realtime)
-- Apply to Supabase PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
CREATE TYPE session_version AS ENUM ('a', 'b');
CREATE TYPE speaker_type AS ENUM ('student', 'orchestrator', 'math', 'history', 'english', 'teacher');
CREATE TYPE job_status AS ENUM ('pending', 'processing', 'complete', 'error');

-- learning_sessions: tracks each student demo session
CREATE TABLE IF NOT EXISTS learning_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version session_version NOT NULL,
    student_id TEXT,
    room_name TEXT,       -- Version A: LiveKit room name
    session_token TEXT,   -- Version B: OpenAI session token
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_learning_sessions_version ON learning_sessions(version);
CREATE INDEX idx_learning_sessions_started ON learning_sessions(started_at DESC);

-- transcript_turns: individual utterances in a session
CREATE TABLE IF NOT EXISTS transcript_turns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    speaker speaker_type NOT NULL,
    text TEXT NOT NULL,
    subject TEXT,         -- 'math'|'history'|'english' for specialist turns
    turn_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transcript_turns_session ON transcript_turns(session_id, turn_index);
CREATE INDEX idx_transcript_turns_created ON transcript_turns(created_at DESC);

-- routing_decisions: log every routing choice the orchestrator makes
CREATE TABLE IF NOT EXISTS routing_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    from_agent TEXT NOT NULL,  -- 'orchestrator'
    to_agent TEXT NOT NULL,    -- 'math'|'history'|'english'|'teacher'
    confidence FLOAT,
    transcript_excerpt TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_routing_decisions_session ON routing_decisions(session_id);

-- escalation_events: teacher escalation requests
CREATE TABLE IF NOT EXISTS escalation_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    version session_version NOT NULL,
    reason TEXT,
    -- Version A: LiveKit JWT for teacher to join room with audio/video
    teacher_token TEXT,
    -- Version B: WebSocket URL for teacher observer (transcript + text injection)
    teacher_ws_url TEXT,
    teacher_joined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_escalation_events_session ON escalation_events(session_id);

-- guardrail_events: log all content moderation decisions
CREATE TABLE IF NOT EXISTS guardrail_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES learning_sessions(id) ON DELETE SET NULL,
    original_text TEXT NOT NULL,
    rewritten_text TEXT,
    categories_flagged TEXT[] DEFAULT '{}',
    flagged BOOLEAN NOT NULL DEFAULT false,
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_guardrail_events_session ON guardrail_events(session_id);
CREATE INDEX idx_guardrail_events_flagged ON guardrail_events(flagged) WHERE flagged = true;

-- Enable Supabase Realtime for live teacher UI updates
ALTER PUBLICATION supabase_realtime ADD TABLE escalation_events;
ALTER PUBLICATION supabase_realtime ADD TABLE transcript_turns;
