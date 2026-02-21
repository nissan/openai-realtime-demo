"""Session state for Version B (no LiveKit dependencies)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionUserdata:
    """
    Per-session state for Version B backend.
    Adapted from Version A's SessionUserdata — no LiveKit deps.

    CRITICAL: skip_next_user_turns is an int counter, never a string flag.
    filler_state is an int counter (0/1/2/3), never a string threshold name.
    """
    session_id: str = ""
    skip_next_user_turns: int = 0
    current_subject: Optional[str] = None
    filler_state: int = 0  # 0=none, 1=500ms, 2=1500ms, 3=3000ms
    escalated: bool = False
    turn_count: int = 0

    def should_skip_turn(self) -> bool:
        return self.skip_next_user_turns > 0

    def mark_routing(self) -> None:
        self.skip_next_user_turns += 1

    def consume_skip(self) -> None:
        if self.skip_next_user_turns > 0:
            self.skip_next_user_turns -= 1

    def next_filler_threshold(self) -> Optional[float]:
        """Returns next filler delay in seconds, or None if all thresholds used."""
        thresholds = {0: 0.5, 1: 1.5, 2: 3.0}
        return thresholds.get(self.filler_state)

    def advance_filler(self) -> None:
        """Move to next filler threshold."""
        self.filler_state = min(self.filler_state + 1, 3)

    def reset_filler(self) -> None:
        """Reset filler state after job completes."""
        self.filler_state = 0
