import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
WORKERS_PATH = DATA_DIR / "workers.json"
PLAN_PATH = DATA_DIR / "daily_plan.json"


# ---------------------------------------------------------------------------
# loading and saving
# ---------------------------------------------------------------------------

def _load_workers() -> list[dict]:
    with open(WORKERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_workers(workers: list[dict]) -> None:
    with open(WORKERS_PATH, "w", encoding="utf-8") as f:
        json.dump(workers, f, indent=2)


def _load_plan() -> dict:
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_worker(workers: list[dict], worker_id: str) -> dict | None:
    return next((w for w in workers if w["worker_id"] == worker_id), None)


# ---------------------------------------------------------------------------
# read-only tools
# ---------------------------------------------------------------------------

def get_worker(worker_id: str) -> dict:
    workers = _load_workers()
    worker = _find_worker(workers, worker_id)
    if worker is None:
        return {"status": "error", "message": f"No worker found with id '{worker_id}'."}
    return {"status": "ok", "worker": worker}


def search_workers(query: str) -> dict:
    workers = _load_workers()
    q = query.lower()
    matches = [w for w in workers if q in w["worker_name"].lower()]
    return {"status": "ok", "count": len(matches), "workers": matches}


def get_daily_plan() -> dict:
    return {"status": "ok", "plan": _load_plan()}


def list_open_cells() -> dict:
    """Compare who's actually present against each cell's required headcount."""
    workers = _load_workers()
    plan = _load_plan()
    open_cells = []
    for line in plan["lines"]:
        for cell in line["cells"]:
            present = sum(
                1 for w in workers
                if w["current_line"] == line["line"]
                and w["current_cell"] == cell["cell"]
                and w["present_today"]
                and w["employment_status"] == "active"
            )
            required = cell["required_workers"]
            if present < required:
                open_cells.append({
                    "line": line["line"],
                    "cell": cell["cell"],
                    "present": present,
                    "required": required,
                    "short_by": required - present,
                })
    return {"status": "ok", "open_cells": open_cells}


# ---------------------------------------------------------------------------
# gating brain
# ---------------------------------------------------------------------------

DESTRUCTIVE_TOOLS = {"terminate_worker", "delete_worker"}
SENSITIVE_UPDATE_FIELDS = {"employment_status"}
ANOMALY_THRESHOLD = 0.4  # a reading more than 40% off baseline gets flagged


def _is_anomalous_output(worker: dict, parts_made: int) -> bool:
    baseline = worker["avg_hourly_output"]
    if baseline == 0:
        return True  # no baseline to compare against -- play it safe
    deviation = abs(parts_made - baseline) / baseline
    return deviation > ANOMALY_THRESHOLD


def requires_approval(tool: str, args: dict, workers: list[dict]) -> bool:
    if tool in DESTRUCTIVE_TOOLS:
        return True

    if tool == "update_worker":
        updates = args.get("updates", {})
        return any(field in SENSITIVE_UPDATE_FIELDS for field in updates)

    if tool == "log_hourly_output":
        worker = _find_worker(workers, args["worker_id"])
        if worker is None:
            return False  # precheck will catch the missing worker
        return _is_anomalous_output(worker, args["parts_made"])

    return False


# ---------------------------------------------------------------------------
# precheck -- catches a bad call before anyone gets bothered
# ---------------------------------------------------------------------------

UPDATE_WORKER_EDITABLE_FIELDS = {"skill_level", "employment_status", "notes", "age"}

NEEDS_TARGET_WORKER = {
    "update_worker", "terminate_worker", "delete_worker",
    "log_hourly_output", "allocate_worker", "mark_attendance",
}


def precheck(tool: str, args: dict, workers: list[dict]) -> dict | None:
    if tool in NEEDS_TARGET_WORKER:
        worker = _find_worker(workers, args.get("worker_id"))
        if worker is None:
            return {"status": "error", "message": f"No worker found with id '{args.get('worker_id')}'."}

    if tool == "update_worker":
        updates = args.get("updates", {}) or {}
        bad_fields = [f for f in updates if f not in UPDATE_WORKER_EDITABLE_FIELDS]
        if bad_fields:
            return {
                "status": "error",
                "message": f"Cannot update field(s) {bad_fields} via update_worker. "
                            f"Use log_hourly_output to record output/rejected parts.",
            }
        if not updates:
            return {"status": "error", "message": "No fields provided to update."}

    return None


# ---------------------------------------------------------------------------
# mutations
# ---------------------------------------------------------------------------

READ_ONLY_TOOLS = {"get_worker", "search_workers", "get_daily_plan", "list_open_cells"}


def _apply_mutation(tool: str, args: dict, workers: list[dict]) -> dict:
    worker = _find_worker(workers, args["worker_id"])

    if tool == "mark_attendance":
        worker["present_today"] = args["present"]
        return {"status": "ok", "worker": worker}

    if tool == "allocate_worker":
        worker["current_line"] = args["line"]
        worker["current_cell"] = args["cell"]
        return {"status": "ok", "worker": worker}

    if tool == "update_worker":
        worker.update(args["updates"])
        return {"status": "ok", "worker": worker}

    if tool == "log_hourly_output":
        worker["total_parts_made"] += args["parts_made"]
        worker["rejected_parts"] += args["rejected_parts"]
        good_parts = worker["total_parts_made"] - worker["rejected_parts"]
        worker["efficiency"] = round((good_parts / worker["total_parts_made"]) * 100, 1)
        return {"status": "ok", "worker": worker}

    if tool == "terminate_worker":
        worker["employment_status"] = "terminated"
        worker["present_today"] = False
        worker["current_line"] = None
        worker["current_cell"] = None
        return {"status": "ok", "worker": worker}

    if tool == "delete_worker":
        workers.remove(worker)
        return {"status": "deleted", "worker_id": args["worker_id"]}

    return {"status": "error", "message": f"Unknown tool '{tool}'."}


# ---------------------------------------------------------------------------
# the single entry point server.py calls for every tool
# ---------------------------------------------------------------------------

def handle_tool_call(tool: str, args: dict, approve_fn=None) -> dict:
    if tool in READ_ONLY_TOOLS:
        if tool == "get_worker":
            return get_worker(args["worker_id"])
        if tool == "search_workers":
            return search_workers(args["query"])
        if tool == "get_daily_plan":
            return get_daily_plan()
        if tool == "list_open_cells":
            return list_open_cells()

    workers = _load_workers()

    err = precheck(tool, args, workers)
    if err is not None:
        return err

    if requires_approval(tool, args, workers):
        if approve_fn is None:
            return {"status": "rejected", "reason": "No approval channel available; failing closed."}
        approved, reason = approve_fn(tool, args)
        if not approved:
            return {"status": "rejected", "reason": reason or "Denied by human reviewer."}

    result = _apply_mutation(tool, args, workers)
    _save_workers(workers)
    return result