"""Security audit records without storing credentials or raw secrets."""

from datetime import UTC, datetime
from typing import Any


def audit_event(
    *,
    subject: str,
    action: str,
    resource: str,
    outcome: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_metadata = {
        key: value
        for key, value in (metadata or {}).items()
        if key.lower() not in {"token", "authorization", "api_key", "password", "secret"}
    }
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "subject": subject,
        "action": action,
        "resource": resource,
        "outcome": outcome,
        "metadata": safe_metadata,
    }
