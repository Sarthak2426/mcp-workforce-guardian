from fastmcp import FastMCP

import core
import approval_broker

mcp = FastMCP("workforce-guardian")


@mcp.tool()
def get_worker(worker_id: str) -> dict:
    """Look up a single worker by id. Safe, read-only, never requires approval."""
    return core.handle_tool_call("get_worker", {"worker_id": worker_id})


@mcp.tool()
def search_workers(query: str) -> dict:
    """Search workers by name substring (case-insensitive). Safe, read-only."""
    return core.handle_tool_call("search_workers", {"query": query})


@mcp.tool()
def get_daily_plan() -> dict:
    """Get today's production plan: which lines/cells need how many workers."""
    return core.handle_tool_call("get_daily_plan", {})


@mcp.tool()
def list_open_cells() -> dict:
    """List production cells that are currently short-staffed today."""
    return core.handle_tool_call("list_open_cells", {})


@mcp.tool()
def mark_attendance(worker_id: str, present: bool) -> dict:
    """Mark whether a worker is present today. Routine, not gated."""
    return core.handle_tool_call(
        "mark_attendance", {"worker_id": worker_id, "present": present},
        approve_fn=approval_broker.request_approval,
    )


@mcp.tool()
def allocate_worker(worker_id: str, line: str, cell: str) -> dict:
    """Assign a worker to a production line/cell. Routine, not gated."""
    return core.handle_tool_call(
        "allocate_worker", {"worker_id": worker_id, "line": line, "cell": cell},
        approve_fn=approval_broker.request_approval,
    )


@mcp.tool()
def update_worker(worker_id: str, updates: dict) -> dict:
    """
    Update a worker's editable fields (skill_level, employment_status, notes,
    age). Edits touching employment_status require human approval. To record
    hourly output/rejected parts, use log_hourly_output instead -- this tool
    cannot touch those fields.
    """
    return core.handle_tool_call(
        "update_worker", {"worker_id": worker_id, "updates": updates},
        approve_fn=approval_broker.request_approval,
    )


@mcp.tool()
def log_hourly_output(worker_id: str, parts_made: int, rejected_parts: int) -> dict:
    """
    Record this hour's output for a worker. If the reported numbers deviate
    significantly from the worker's normal rate, this requires human
    approval before being committed -- guards against misheard or
    misparsed numbers being written straight into the record.
    """
    return core.handle_tool_call(
        "log_hourly_output",
        {"worker_id": worker_id, "parts_made": parts_made, "rejected_parts": rejected_parts},
        approve_fn=approval_broker.request_approval,
    )


@mcp.tool()
def terminate_worker(worker_id: str) -> dict:
    """Terminate a worker's employment. Always requires human approval."""
    return core.handle_tool_call(
        "terminate_worker", {"worker_id": worker_id},
        approve_fn=approval_broker.request_approval,
    )


@mcp.tool()
def delete_worker(worker_id: str) -> dict:
    """Permanently delete a worker's record. Always requires human approval."""
    return core.handle_tool_call(
        "delete_worker", {"worker_id": worker_id},
        approve_fn=approval_broker.request_approval,
    )


if __name__ == "__main__":
    mcp.run()