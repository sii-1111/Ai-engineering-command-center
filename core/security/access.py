"""Request-level authentication and least-privilege authorization."""

from dataclasses import dataclass
import hashlib
import os
from typing import Any

from core.security.tool_policy import DEFAULT_TOOL_POLICY, ToolDecision


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]

    def can(self, permission: str) -> bool:
        permissions = {
            "viewer": {"task:read"},
            "engineer": {"task:read", "task:create", "task:approve"},
            "admin": {"task:read", "task:create", "task:approve", "security:admin"},
        }
        return bool(permissions.get("admin", set()) if "admin" in self.roles else set().union(
            *(permissions.get(role, set()) for role in self.roles)
        ) & {permission})


def authenticate_token(token: str | None) -> Principal | None:
    expected = os.getenv("COMMAND_CENTER_API_TOKEN")
    if not expected or not token:
        return None
    if not _constant_time_equal(token, expected):
        return None
    role = os.getenv("COMMAND_CENTER_API_ROLE", "engineer")
    subject = hashlib.sha256(token.encode()).hexdigest()[:16]
    return Principal(subject=subject, roles=frozenset({role}))


def _constant_time_equal(left: str, right: str) -> bool:
    import hmac
    return hmac.compare_digest(left, right)


def authorize_task(principal: Principal, permission: str) -> None:
    if not principal.can(permission):
        raise PermissionError(f"Principal '{principal.subject}' lacks '{permission}'.")


def authorize_tool(principal: Principal, agent: str, tool: str) -> ToolDecision:
    authorize_task(principal, "task:create")
    decision = DEFAULT_TOOL_POLICY.authorize(agent, tool)
    if not decision.allowed:
        raise PermissionError(decision.reason)
    if decision.risk in {"high", "critical"}:
        authorize_task(principal, "task:approve")
    return decision
