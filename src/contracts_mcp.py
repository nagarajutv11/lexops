"""Contract repository and e-signature mock, exposed only as an MCP server.

Paths resolve from this file and must stay inside the sandbox. A path escape
or a symlink is a tool error. There is no delete, no arbitrary write, and no
tool that approves as counsel.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fastmcp import FastMCP

from catalog import load_contracts, load_signature_requests

SERVER_ROOT = Path(__file__).resolve().parent
DEFAULT_SANDBOX = SERVER_ROOT / "contract_sandbox"
TOOL_NAMES = (
    "list_contracts",
    "read_contract",
    "search_contracts",
    "create_envelope",
    "list_envelopes",
)


def _is_link(path: Path) -> bool:
    return path.is_symlink()


def safe_path(relative: str, root: Path) -> Path:
    if not relative or relative.startswith(("/", "\\")) or ":" in relative:
        raise ValueError(f"path escapes the sandbox: {relative!r}")
    root_resolved = root.resolve()
    raw = root_resolved / relative
    if _is_link(raw):
        raise ValueError(f"symlinks are not allowed: {relative!r}")
    candidate = raw.resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError(f"path escapes the sandbox: {relative!r}")
    return candidate


def _envelope_file(root: Path) -> Path:
    return root / "envelopes.json"


def _created(root: Path) -> list[dict]:
    path = _envelope_file(root)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data)


def _write_created(root: Path, rows: list[dict]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _envelope_file(root).write_text(json.dumps(rows, indent=2), encoding="utf-8")


def list_contracts() -> list[dict]:
    return [
        {
            "contract_id": row.contract_id,
            "counterparty_id": row.counterparty_id,
            "contract_type": row.contract_type,
            "status": row.status,
            "term_months": row.term_months,
            "renewal_notice_days": row.renewal_notice_days,
            "risk_score": row.risk_score,
        }
        for row in load_contracts()
    ]


def search_contracts(counterparty_id: str) -> list[dict]:
    return [row for row in list_contracts() if row["counterparty_id"] == counterparty_id]


def read_contract(relative_path: str, root: Path | None = None) -> dict:
    sandbox = root or DEFAULT_SANDBOX
    try:
        path = safe_path(relative_path, sandbox)
    except ValueError as exc:
        return {"error": str(exc)}
    if not path.is_file():
        return {"error": f"contract file is not in the sandbox: {relative_path}"}
    return {"path": relative_path, "text": path.read_text(encoding="utf-8")}


def create_envelope(contract_id: str, signer_email: str, root: Path | None = None) -> dict:
    sandbox = root or DEFAULT_SANDBOX
    known = {row.contract_id for row in load_contracts()}
    if contract_id not in known:
        return {"error": f"unknown contract {contract_id}"}
    rows = _created(sandbox)
    envelope_id = f"NW-SIG-LOCAL-{len(rows):05d}"
    row = {
        "envelope_id": envelope_id,
        "contract_id": contract_id,
        "status": "created",
        "signer_email": signer_email,
    }
    rows.append(row)
    _write_created(sandbox, rows)
    return row


def list_envelopes(root: Path | None = None) -> list[dict]:
    sandbox = root or DEFAULT_SANDBOX
    rows = [asdict(row) for row in load_signature_requests()]
    rows.extend(_created(sandbox))
    return rows


def build_server(root: Path | None = None) -> FastMCP:
    sandbox = root or DEFAULT_SANDBOX
    sandbox.mkdir(parents=True, exist_ok=True)
    mcp = FastMCP("lexops-contracts")

    @mcp.tool
    def list_contracts_tool() -> list[dict]:
        """List LexOps contracts. There is no delete tool."""
        return list_contracts()

    @mcp.tool
    def read_contract_tool(relative_path: str) -> dict:
        """Read one contract file inside the sandbox."""
        return read_contract(relative_path, sandbox)

    @mcp.tool
    def search_contracts_tool(counterparty_id: str) -> list[dict]:
        """Search contracts for one counterparty."""
        return search_contracts(counterparty_id)

    @mcp.tool
    def create_envelope_tool(contract_id: str, signer_email: str) -> dict:
        """Create an e-signature envelope. This does not approve as counsel."""
        return create_envelope(contract_id, signer_email, sandbox)

    @mcp.tool
    def list_envelopes_tool() -> list[dict]:
        """List e-signature envelopes."""
        return list_envelopes(sandbox)

    mcp._lexops_tool_names = {  # type: ignore[attr-defined]
        "list_contracts_tool": "list_contracts",
        "read_contract_tool": "read_contract",
        "search_contracts_tool": "search_contracts",
        "create_envelope_tool": "create_envelope",
        "list_envelopes_tool": "list_envelopes",
    }
    return mcp


def _unwrap(result):
    data = getattr(result, "data", None)
    if data is not None:
        return data
    if isinstance(result, dict):
        return result
    content = getattr(result, "content", None) or []
    if content:
        text = getattr(content[0], "text", "")
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return {"raw": str(result)}


class McpContractClient:
    """The only door the team uses for contracts and envelopes."""

    def __init__(self, server: FastMCP | None = None) -> None:
        self.server = server or build_server()

    def call(self, name: str, arguments: dict | None = None):
        import asyncio

        from fastmcp import Client

        tool_name = f"{name}_tool" if not name.endswith("_tool") else name

        async def _run():
            async with Client(self.server) as client:
                return await client.call_tool(tool_name, arguments or {})

        try:
            return _unwrap(asyncio.run(_run()))
        except Exception as exc:
            return {"error": str(exc)}
