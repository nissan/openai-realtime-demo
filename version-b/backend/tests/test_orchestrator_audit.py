"""
Unit tests for orchestrator audit trail population.

Tests:
- routing_decisions INSERT on classification
- guardrail_events INSERT when flagged/clean
- raw_text vs safe_text separation via tee stream
- learning_sessions INSERT on session token creation
- DB errors in audit functions do not break orchestration
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../shared"))


@pytest.fixture
def mock_pool_conn():
    """Returns (pool, conn) pair where conn.execute is an AsyncMock."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__ = AsyncMock(return_value=conn)
    ctx_mgr.__aexit__ = AsyncMock(return_value=False)
    pool = AsyncMock()
    pool.acquire = MagicMock(return_value=ctx_mgr)
    return pool, conn


@pytest.mark.asyncio
async def test_routing_decision_inserted_on_classification(mock_pool_conn):
    """_log_routing_decision inserts a row into routing_decisions with confidence + excerpt."""
    pool, conn = mock_pool_conn
    from datetime import datetime, timezone

    with patch("backend.services.transcript_store.get_pool", new=AsyncMock(return_value=pool)):
        from backend.routers.orchestrator import _log_routing_decision
        await _log_routing_decision(
            "sess-1", "math", datetime.now(timezone.utc),
            confidence=1.0,
            transcript_excerpt="What is 25% of 80?",
        )

    conn.execute.assert_called_once()
    sql = conn.execute.call_args[0][0]
    assert "INSERT INTO routing_decisions" in sql
    assert "orchestrator" in sql
    assert "confidence" in sql
    assert "transcript_excerpt" in sql
    # Verify bound params include session_id, to_agent, confidence, excerpt
    args = conn.execute.call_args[0]
    assert "sess-1" in args
    assert "math" in args
    assert 1.0 in args
    assert "What is 25% of 80?" in args


@pytest.mark.asyncio
async def test_guardrail_event_inserted_when_flagged(mock_pool_conn):
    """_log_guardrail_event inserts with flagged=True, confidence, and categories_flagged."""
    pool, conn = mock_pool_conn

    with patch("backend.services.transcript_store.get_pool", new=AsyncMock(return_value=pool)):
        from backend.routers.orchestrator import _log_guardrail_event
        await _log_guardrail_event(
            session_id="sess-2",
            original="bad content here",
            rewritten="appropriate content here",
            flagged=True,
            confidence=0.95,
            categories_flagged=["harassment"],
        )

    conn.execute.assert_called_once()
    sql = conn.execute.call_args[0][0]
    assert "INSERT INTO guardrail_events" in sql
    assert "confidence" in sql
    assert "categories_flagged" in sql
    args = conn.execute.call_args[0]
    assert "sess-2" in args
    assert True in args              # flagged=True
    assert 0.95 in args              # confidence
    assert ["harassment"] in args    # categories_flagged
    # query + 6 value params = 7 total positional args
    assert len(args) == 7


@pytest.mark.asyncio
async def test_guardrail_event_inserted_when_clean(mock_pool_conn):
    """_log_guardrail_event inserts with flagged=False when text is unchanged."""
    pool, conn = mock_pool_conn

    with patch("backend.services.transcript_store.get_pool", new=AsyncMock(return_value=pool)):
        from backend.routers.orchestrator import _log_guardrail_event
        await _log_guardrail_event(
            session_id="sess-3",
            original="clean answer",
            rewritten="clean answer",
            flagged=False,
        )

    conn.execute.assert_called_once()
    args = conn.execute.call_args[0]
    assert False in args  # flagged=False


@pytest.mark.asyncio
async def test_raw_text_differs_from_safe_text_when_guardrail_rewrites():
    """When guardrail rewrites, raw_text != safe_text and both are captured."""
    from backend.models.job import OrchestratorJob
    from backend.models.session_state import SessionUserdata

    job = OrchestratorJob(session_id="sess-4", student_text="test question")
    session = SessionUserdata(session_id="sess-4")

    raw_response = "raw harmful chunk"
    safe_response = "safe rewritten chunk"

    async def mock_classifier(text, client=None):
        result = MagicMock()
        result.subject = "math"
        result.confidence = 1.0
        return result

    async def mock_specialist_stream(text):
        yield raw_response

    async def mock_guardrail(stream, client=None):
        async for _ in stream:
            yield safe_response  # guardrail rewrites

    mock_classifier_mod = MagicMock()
    mock_classifier_mod.route_intent = mock_classifier
    mock_math_mod = MagicMock()
    mock_math_mod.stream_math_response = lambda text: mock_specialist_stream(text)
    mock_guardrail_service = MagicMock()
    mock_guardrail_service.check_stream_with_sentence_buffer = mock_guardrail

    with (
        patch.dict(sys.modules, {
            "specialists": MagicMock(),
            "specialists.classifier": mock_classifier_mod,
            "specialists.math": mock_math_mod,
            "guardrail": MagicMock(),
            "guardrail.service": mock_guardrail_service,
        }),
        patch("backend.routers.orchestrator._log_routing_decision", new=AsyncMock()),
        patch("backend.routers.orchestrator._log_guardrail_event", new=AsyncMock()) as mock_log_guard,
        patch("backend.routers.orchestrator._save_transcript", new=AsyncMock()),
    ):
        from backend.routers.orchestrator import _run_orchestration
        await _run_orchestration(job, session)

    # Verify guardrail event was called with different raw vs safe text
    mock_log_guard.assert_called_once()
    call_kwargs = mock_log_guard.call_args
    original = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else call_kwargs[1].get("original", "")
    rewritten = call_kwargs[0][2] if len(call_kwargs[0]) > 2 else call_kwargs[1].get("rewritten", "")
    assert original == raw_response
    assert rewritten == safe_response
    assert original != rewritten


@pytest.mark.asyncio
async def test_learning_session_inserted_on_token_creation(mock_pool_conn):
    """_create_learning_session inserts a row into learning_sessions."""
    pool, conn = mock_pool_conn

    with patch("backend.services.transcript_store.get_pool", new=AsyncMock(return_value=pool)):
        from backend.routers.session import _create_learning_session
        await _create_learning_session("sess-5", token_prefix="test-prefix-123")

    conn.execute.assert_called_once()
    sql = conn.execute.call_args[0][0]
    assert "INSERT INTO learning_sessions" in sql
    args = conn.execute.call_args[0]
    assert "sess-5" in args
    assert "b" in args  # version='b'


@pytest.mark.asyncio
async def test_audit_failures_do_not_break_orchestration():
    """DB errors inside audit functions do not cause orchestration to fail.

    The audit functions (_log_routing_decision, _log_guardrail_event) each
    have their own try/except so a DB failure only logs a warning and never
    propagates to the main orchestration flow.
    """
    from backend.models.job import OrchestratorJob
    from backend.models.session_state import SessionUserdata

    job = OrchestratorJob(session_id="sess-6", student_text="What is 2+2?")
    session = SessionUserdata(session_id="sess-6")

    async def mock_classifier(text, client=None):
        result = MagicMock()
        result.subject = "math"
        result.confidence = 1.0
        return result

    async def mock_specialist_stream(text):
        yield "The answer is 4."

    async def mock_guardrail(stream, client=None):
        async for chunk in stream:
            yield chunk

    mock_classifier_mod = MagicMock()
    mock_classifier_mod.route_intent = mock_classifier
    mock_math_mod = MagicMock()
    mock_math_mod.stream_math_response = lambda text: mock_specialist_stream(text)
    mock_guardrail_service = MagicMock()
    mock_guardrail_service.check_stream_with_sentence_buffer = mock_guardrail

    # Make the DB pool raise — the audit functions catch this internally
    async def failing_get_pool():
        raise Exception("DB connection refused")

    with (
        patch.dict(sys.modules, {
            "specialists": MagicMock(),
            "specialists.classifier": mock_classifier_mod,
            "specialists.math": mock_math_mod,
            "guardrail": MagicMock(),
            "guardrail.service": mock_guardrail_service,
        }),
        patch("backend.services.transcript_store.get_pool", new=failing_get_pool),
        patch("backend.routers.orchestrator._save_transcript", new=AsyncMock()),
    ):
        from backend.routers.orchestrator import _run_orchestration
        # Should NOT raise despite DB errors in audit logging
        await _run_orchestration(job, session)

    # Job should still complete successfully
    assert job.status.value == "complete"
    assert job.tts_ready is True
    assert job.safe_text is not None
