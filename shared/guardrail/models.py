"""Data models for guardrail results."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ModerationResult:
    """Result from content moderation check."""
    flagged: bool
    categories_flagged: List[str] = field(default_factory=list)
    original_text: str = ""
    rewritten_text: Optional[str] = None
    confidence: float = 0.0

    @property
    def safe_text(self) -> str:
        """Return rewritten text if flagged, otherwise original."""
        if self.flagged and self.rewritten_text:
            return self.rewritten_text
        return self.original_text
