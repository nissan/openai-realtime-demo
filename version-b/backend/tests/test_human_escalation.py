"""Unit tests for human_escalation service (version-b)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.services.human_escalation import (
    add_teacher_connection,
    remove_teacher_connection,
    broadcast_to_teachers,
    _teacher_connections,
)


@pytest.fixture(autouse=True)
def clear_connections():
    _teacher_connections.clear()
    yield
    _teacher_connections.clear()


def test_add_teacher_connection_creates_set():
    ws = MagicMock()
    add_teacher_connection("sess-1", ws)
    assert ws in _teacher_connections["sess-1"]


def test_add_teacher_connection_multiple_teachers():
    ws1, ws2 = MagicMock(), MagicMock()
    add_teacher_connection("sess-2", ws1)
    add_teacher_connection("sess-2", ws2)
    assert len(_teacher_connections["sess-2"]) == 2


def test_remove_teacher_connection_discards_ws():
    ws = MagicMock()
    add_teacher_connection("sess-3", ws)
    remove_teacher_connection("sess-3", ws)
    assert ws not in _teacher_connections.get("sess-3", set())


def test_remove_nonexistent_connection_is_safe():
    """remove_teacher_connection on unknown session must not raise."""
    remove_teacher_connection("unknown-sess", MagicMock())  # should not raise


@pytest.mark.asyncio
async def test_broadcast_to_teachers_sends_to_all():
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    add_teacher_connection("sess-4", ws1)
    add_teacher_connection("sess-4", ws2)
    await broadcast_to_teachers("sess-4", {"type": "transcript", "text": "hello"})
    ws1.send_json.assert_awaited_once()
    ws2.send_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_broadcast_removes_disconnected_ws():
    """broadcast_to_teachers prunes WebSockets that throw on send."""
    ws_ok = AsyncMock()
    ws_dead = AsyncMock()
    ws_dead.send_json.side_effect = Exception("connection closed")
    add_teacher_connection("sess-5", ws_ok)
    add_teacher_connection("sess-5", ws_dead)
    await broadcast_to_teachers("sess-5", {"type": "ping"})
    # Dead websocket should be pruned
    assert ws_dead not in _teacher_connections.get("sess-5", set())
    assert ws_ok in _teacher_connections["sess-5"]
