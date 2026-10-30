"""Maps the engine's raw severities to the five user-facing status labels.

critical -> HIGH_RISK, high -> SUSPICIOUS, medium -> NEEDS_REVIEW, low -> LOW_OBSERVED_RISK.
Anything else (including "unknown") -> UNKNOWN. A missing result is never mapped to a safe label.
"""

STATUS_LABELS = ["HIGH_RISK", "SUSPICIOUS", "NEEDS_REVIEW", "LOW_OBSERVED_RISK", "UNKNOWN"]

_MAP = {
    "critical": "HIGH_RISK",
    "high": "SUSPICIOUS",
    "medium": "NEEDS_REVIEW",
    "low": "LOW_OBSERVED_RISK",
}


def to_status_label(severity: str) -> str:
    return _MAP.get((severity or "").lower(), "UNKNOWN")
