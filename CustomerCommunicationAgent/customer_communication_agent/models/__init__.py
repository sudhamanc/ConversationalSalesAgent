"""Notification statuses and legacy type aliases for the Customer Communication Agent."""

from enum import Enum


class NotificationStatus(str, Enum):
    """Values of ``notifications.status``."""

    PENDING = "pending"        # enqueued, not yet delivered (or retrying after an error)
    SENT = "sent"              # delivered via SMTP
    SIMULATED = "simulated"    # SMTP disabled; delivery logged only
    DEDUPED = "deduped"        # identical notification sent within the dedup window
    FAILED = "failed"          # gave up after MAX_ATTEMPTS or undeliverable


#: Pre-outbox type names (as the LLM or old history may use them) -> outbox types.
LEGACY_TYPE_ALIASES = {
    "quote_saved": "quote_confirmation",
    "payment_success": "payment_confirmation",
    "payment_failed": "payment_confirmation",
    "install_scheduled": "installation_scheduled",
    "install_reminder": "installation_reminder",
    "install_complete": "installation_complete",
}


def normalize_type(notification_type: str) -> str:
    """Lower-case a type name and map legacy aliases to outbox types."""
    key = notification_type.strip().lower().replace("-", "_")
    return LEGACY_TYPE_ALIASES.get(key, key)


__all__ = ["NotificationStatus", "LEGACY_TYPE_ALIASES", "normalize_type"]
