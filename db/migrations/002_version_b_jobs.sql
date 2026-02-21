-- Migration 002: Version B orchestrator jobs table
-- Only needed for Version B (FastAPI backend with async job dispatch)

-- orchestrator_jobs: async job tracking for Version B backend
CREATE TABLE IF NOT EXISTS orchestrator_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES learning_sessions(id) ON DELETE SET NULL,
    status job_status NOT NULL DEFAULT 'pending',

    -- Input
    student_text TEXT NOT NULL,

    -- Routing result
    subject TEXT,         -- 'math'|'history'|'english'

    -- Output
    raw_text TEXT,        -- LLM response before guardrail
    safe_text TEXT,       -- Guardrailed response (use this for TTS)
    tts_ready BOOLEAN NOT NULL DEFAULT false,  -- Set true when safe_text ready

    -- Error handling
    error_message TEXT,

    -- Timing audit
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    classified_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- TTL cleanup (Redis handles in-memory; this is for audit trail)
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 hour'
);

CREATE INDEX idx_orchestrator_jobs_session ON orchestrator_jobs(session_id);
CREATE INDEX idx_orchestrator_jobs_status ON orchestrator_jobs(status);
CREATE INDEX idx_orchestrator_jobs_expires ON orchestrator_jobs(expires_at);

-- Enforce valid status values
ALTER TABLE orchestrator_jobs ADD CONSTRAINT chk_job_status
    CHECK (status IN ('pending', 'processing', 'complete', 'error'));

COMMENT ON TABLE orchestrator_jobs IS
    'Version B async job tracking. Flow:
     POST /orchestrate -> pending (job_id returned <100ms)
     classifier starts -> processing
     specialist stream + guardrail -> complete (tts_ready=true)
     client polls GET /orchestrate/{job_id} until tts_ready, then streams POST /tts/stream.';
