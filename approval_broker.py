"""
approval_broker.py — the human-in-the-loop side channel.

server.py can't just call input() to ask a human something directly,
because it talks to Claude Desktop over stdio (stdin/stdout), and that
channel is already busy carrying the MCP protocol itself. So instead:
server.py drops a small request file into approvals/pending/ and waits
(polling approvals/resolved/ once a second) for a matching decision to
show up. approve_cli.py — a separate program with its own real terminal —
is what actually shows a human the request and writes the decision.
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
    """Blocking call: write a pending request, wait for a human (running
    approve_cli.py) to resolve it, return (approved, reason). Fails closed
    (denied) on timeout -- an unanswered destructive request should NOT
    execute by default."""
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
    """Used by approve_cli.py to discover outstanding requests."""
    items = []
    for path in sorted(PENDING_DIR.glob("*.json")):
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