"""Unit tests for Version B SessionUserdata filler threshold logic."""
import pytest
from backend.models.session_state import SessionUserdata


def test_next_filler_threshold_initial():
    s = SessionUserdata(session_id="s")
    assert s.next_filler_threshold() == 0.5


def test_advance_filler_progresses():
    s = SessionUserdata(session_id="s")
    s.advance_filler()
    assert s.next_filler_threshold() == 1.5
    s.advance_filler()
    assert s.next_filler_threshold() == 3.0


def test_advance_filler_caps_at_3():
    s = SessionUserdata(session_id="s")
    for _ in range(5):
        s.advance_filler()
    assert s.filler_state == 3
    assert s.next_filler_threshold() is None


def test_reset_filler_returns_to_zero():
    s = SessionUserdata(session_id="s")
    s.advance_filler()
    s.advance_filler()
    s.reset_filler()
    assert s.filler_state == 0
    assert s.next_filler_threshold() == 0.5
