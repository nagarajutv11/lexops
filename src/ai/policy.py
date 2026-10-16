"""Pure route and the supervisor's authorization. Neither reads the deadline flag.

Standard language at or above the playbook floor auto-approves. Anything else
is the human path. A redraft loop stops at the revision cap and escalates.
"""

from __future__ import annotations

MAX_REVISIONS = 2

AGENT_SCOPES = {
    "extraction": {"summary", "clause_category", "parse_ok", "parse_errors"},
    "playbook": {"playbook_hits", "citations", "retrieved_chunk_ids", "playbook_status"},
    "redline": {"draft_redline", "disclaimer"},
    "legal": {"issues", "legal_review", "risk"},
    "supervisor": {
        "suggested_route",
        "hops",
        "status",
        "contract_record",
        "envelope",
        "records_loaded",
    },
}


def enforce_scope(role: str, update: dict) -> dict:
    """A specialist may write only its own keys. ``log`` is the shared audit list."""
    allowed = AGENT_SCOPES[role] | {"log"}
    illegal = set(update) - allowed
    if illegal:
        raise PermissionError(
            f"agent '{role}' wrote outside its scope: {sorted(illegal)}; allowed={sorted(allowed)}"
        )
    return update


def route_review(state: dict) -> str:
    """Edge function. Unit-test it with a dict. It does not read deadline_flag."""
    if not state.get("parse_ok", True):
        return "human"
    issues = list(state.get("issues") or [])
    if issues and int(state.get("revision_count") or 0) < MAX_REVISIONS:
        return "redraft"
    risk = state.get("risk") or {}
    if risk.get("auto_eligible") and not issues:
        return "auto"
    return "human"


def legal_final_routes(state: dict) -> set[str]:
    """Routes a policy may authorize. Deadline pressure is not one of the inputs."""
    if not state.get("parse_ok", True):
        return {"human"}
    if state.get("injection"):
        return {"human"}
    risk = state.get("risk") or {}
    issues = list(state.get("issues") or [])
    if risk.get("auto_eligible") and not issues:
        return {"auto", "human"}
    return {"human"}


def authorize_route(suggested: str, state: dict) -> str:
    """The supervisor may suggest. This function is what authorizes a final route."""
    if suggested in {"extraction", "playbook", "redline", "legal"}:
        return suggested
    allowed = legal_final_routes(state)
    if suggested in allowed:
        return suggested
    return "human"


def supervisor_policy(state: dict) -> str:
    """Next hop from the state alone. Scheduling is not authorization."""
    if not state.get("records_loaded"):
        return "extraction"
    if state.get("parse_ok") is False:
        return "human"
    if not state.get("summary"):
        return "extraction"
    if state.get("playbook_status") is None:
        return "playbook"
    if not state.get("draft_redline"):
        return "redline"
    if not state.get("legal_review"):
        return "legal"
    return authorize_route(route_review(state), state)
