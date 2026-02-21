"""Unit tests for SessionUserdata - no LiveKit infra needed."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from models.session_state import SessionUserdata


def test_initial_state():
    """Test default session state values."""
    state = SessionUserdata()
    assert state.skip_next_user_turns == 0
    assert state.current_subject is None
    assert not state.escalated
    assert state.turn_count == 0


def test_should_skip_turn_when_zero():
    """Test should_skip_turn returns False when counter is zero."""
    state = SessionUserdata()
    assert not state.should_skip_turn()


def test_mark_routing_increments_counter():
    """Test that mark_routing increments skip counter."""
    state = SessionUserdata()
    state.mark_routing()
    assert state.skip_next_user_turns == 1
    assert state.should_skip_turn()


def test_consume_skip_decrements_counter():
    """Test that consume_skip decrements counter."""
    state = SessionUserdata()
    state.mark_routing()
    state.mark_routing()
    assert state.skip_next_user_turns == 2

    state.consume_skip()
    assert state.skip_next_user_turns == 1
    assert state.should_skip_turn()

    state.consume_skip()
    assert state.skip_next_user_turns == 0
    assert not state.should_skip_turn()


def test_consume_skip_does_not_go_negative():
    """Test that consume_skip is safe when counter is already zero."""
    state = SessionUserdata()
    state.consume_skip()  # Should not raise
    assert state.skip_next_user_turns == 0


def test_routing_sets_subject():
    """Test routing updates current_subject."""
    state = SessionUserdata()
    state.current_subject = "math"
    state.mark_routing()

    assert state.current_subject == "math"
    assert state.skip_next_user_turns == 1


def test_multiple_routings_stack():
    """Test that multiple mark_routing calls stack correctly."""
    state = SessionUserdata()
    state.mark_routing()
    state.mark_routing()
    state.mark_routing()

    assert state.skip_next_user_turns == 3
    for _ in range(3):
        assert state.should_skip_turn()
        state.consume_skip()

    assert not state.should_skip_turn()
