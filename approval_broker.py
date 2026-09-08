"""
File-based approval queue.

The MCP server talks to its client over stdio, so it can't prompt a human
directly. Instead it writes a request into approvals/pending/ and polls
approvals/resolved/ for the answer. approve_cli.py, run in a separate
terminal, is what shows the request to a human and records the decision.
"""

import json
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).parent / "approvals"
PENDING_DIR = BASE_DIR / "pending"
RESOLVED_DIR = BASE_DIR / "resolved"

PENDING_DIR.mkdir(parents=True, exist_ok=True)
RESOLVED_DIR.mkdir(parents=True, exist_ok=True)


def request_approval(tool: str, args: dict, timeout: int = 300) -> tuple[bool, str]:
    """Write a pending request and block until a human resolves it via
    approve_cli.py. Returns (approved, reason). On timeout it fails closed,
    treating no answer as a denial."""
    request_id = str(uuid.uuid4())[:8]
    pending_path = PENDING_DIR / f"{request_id}.json"
    resolved_path = RESOLVED_DIR / f"{request_id}.json"

    payload = {
        "id": request_id,
        "tool": tool,
        "args": args,
        "requested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    pending_path.write_text(json.dumps(payload, indent=2))

    waited = 0
    try:
        while waited < timeout:
            if resolved_path.exists():
                decision = json.loads(resolved_path.read_text())
                return bool(decision.get("approved")), decision.get("reason", "")
            time.sleep(1)
            waited += 1
        return False, f"Timed out after {timeout}s waiting for a human; failing closed."
    finally:
        pending_path.unlink(missing_ok=True)


def list_pending() -> list[dict]:
    """Requests still waiting on a human. A request that already has a file
    in resolved/ is skipped even if the server hasn't removed its pending
    file yet, so a request stops showing the instant it's answered."""
    items = []
    for path in sorted(PENDING_DIR.glob("*.json")):
        if (RESOLVED_DIR / path.name).exists():
            continue
        try:
            items.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return items


def resolve(request_id: str, approved: bool, reason: str = "") -> None:
    """Used by approve_cli.py to record a human's decision."""
    resolved_path = RESOLVED_DIR / f"{request_id}.json"
    resolved_path.write_text(json.dumps({
        "approved": approved,
        "reason": reason,
        "decided_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, indent=2))