from __future__ import annotations

import re
import unicodedata
from typing import TypedDict

from blocked_terms_ptbr import get_blocked_terms

try:
    from better_profanity import profanity
except ImportError:  # Keeps the app usable before dependencies are installed.
    profanity = None


class ModerationResult(TypedDict):
    allowed: bool
    reason: str | None


def normalize_text(value: str) -> str:
    without_accents = unicodedata.normalize("NFKD", value)
    ascii_text = without_accents.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def moderate_pin(name: str, origin: str, message: str = "") -> ModerationResult:
    combined_text = normalize_text(" ".join([name, origin, message]))
    blocked_terms = {normalize_text(term) for term in get_blocked_terms()}

    if any(term in combined_text for term in blocked_terms):
        return {"allowed": False, "reason": "blocked_language"}

    if profanity is not None and profanity.contains_profanity(combined_text):
        return {"allowed": False, "reason": "blocked_language"}

    return {"allowed": True, "reason": None}
