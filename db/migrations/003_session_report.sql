-- Migration 003: Session report snapshot column
-- Adds a JSONB summary document written when a session ends.
--
-- Rationale (from architecture reflection):
--   Audit tables (transcript_turns, routing_decisions, etc.) are good for
--   operational queries. A session_report JSONB written at close time gives
--   operators a self-contained, human-readable document per session without
--   joining four tables. Have both: real-time audit tables AND a snapshot.

ALTER TABLE learning_sessions
    ADD COLUMN IF NOT EXISTS session_report JSONB;

COMMENT ON COLUMN learning_sessions.session_report IS
    'Self-contained session summary written at close time. Structure:
     {
       "turns": <int>,                  -- total transcript turns
       "subjects": ["math","history"],  -- subjects visited
       "escalated": <bool>,             -- whether teacher was escalated
       "guardrail_flags": <int>,        -- number of content flags
       "routing_decisions": [           -- compact audit of each routing choice
         {"to": "math", "confidence": 0.95, "excerpt": "..."}
       ],
       "closed_at": "<ISO-8601>"
     }
     Append-only: once written, treat as immutable audit record.';
