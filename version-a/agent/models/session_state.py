"""
Session state for LiveKit agent workers.
CRITICAL: Use counters (skip_next_user_turns), never string-match LLM output.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionUserdata:
    """
    Per-session state for LiveKit agent.

    CRITICAL: skip_next_user_turns is a counter (int), not a string flag.
    When routing to a specialist, increment this to prevent double-processing.
    Decrement in on_user_turn_completed callback.
    """
    skip_next_user_turns: int = 0
    current_subject: Optional[str] = None  # 'math'|'history'|'english'
    student_id: Optional[str] = None
    session_id: Optional[str] = None
    room_name: Optional[str] = None
    turn_count: int = 0
    escalated: bool = False

    def should_skip_turn(self) -> bool:
        """Check if the next user turn should be skipped."""
        return self.skip_next_user_turns > 0

    def mark_routing(self) -> None:
        """Called when routing to a specialist — prevents re-processing."""
        self.skip_next_user_turns += 1

    def consume_skip(self) -> None:
        """Called after a turn is skipped to decrement counter."""
        if self.skip_next_user_turns > 0:
            self.skip_next_user_turns -= 1
