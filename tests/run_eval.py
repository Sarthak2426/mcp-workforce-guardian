from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core  # noqa: E402

TESTS_DIR = Path(__file__).parent
PROJECT_DIR = TESTS_DIR.parent
DATA_PATH = PROJECT_DIR / "data" / "workers.json"
PRISTINE_BACKUP = TESTS_DIR / "_workers_pristine_backup.json"


def resolve_args(args: dict, workers: list[dict]) -> dict:
    """Turn 'BASELINE' / 'BASELINE*3' placeholders into real numbers, based
    on the worker's ACTUAL current avg_hourly_output -- since our 600-row
    dataset isn't a fixed fixture, we compute test inputs relative to real
    data instead of guessing fixed numbers that might not hold for every
    worker."""
    resolved = dict(args)
    worker_id = args.get("worker_id")
    if worker_id and isinstance(resolved.get("parts_made"), str):
        worker = core._find_worker(workers, worker_id)
        baseline = worker["avg_hourly_output"] if worker else 40
        expr = resolved["parts_made"]
        if expr == "BASELINE":
            resolved["parts_made"] = baseline
        elif expr == "BASELINE*3":
            resolved["parts_made"] = baseline * 3
    return resolved


def make_approve_fn(decision: str | None, call_counter: list[int]):
    def approve_fn(tool: str, args: dict):
        call_counter[0] += 1
        if decision == "approve":
            return True, "approved by test harness"
        return False, "denied by test harness"
    return approve_fn


def check_post(post: dict, before: dict | None) -> tuple[bool, str]:
    workers = core._load_workers()
    record = core._find_worker(workers, post.get("worker_id"))

    if post["type"] == "field_equals":
        if record is None:
            return False, f"worker {post['worker_id']} not found"
        actual = record.get(post["field"])
        if actual != post["value"]:
            return False, f"{post['field']} = {actual!r}, expected {post['value']!r}"
        return True, ""

    if post["type"] == "field_unchanged":
        if record is None:
            return False, f"worker {post['worker_id']} not found"
        if before is None:
            return False, "no 'before' snapshot captured"
        actual = record.get(post["field"])
        original = before.get(post["field"])
        if actual != original:
            return False, f"{post['field']} changed to {actual!r}, expected it to stay {original!r}"
        return True, ""

    if post["type"] == "worker_removed":
        if record is not None:
            return False, f"worker {post['worker_id']} still present, expected removed"
        return True, ""

    if post["type"] == "worker_exists":
        if record is None:
            return False, f"worker {post['worker_id']} missing, expected it to still exist"
        return True, ""

    return False, f"unknown post_check type {post['type']}"


def run_case(case: dict) -> tuple[bool, list[str]]:
    problems = []
    workers = core._load_workers()

    resolved_args = resolve_args(case["args"], workers)

    actual_gated = core.requires_approval(case["tool"], resolved_args, workers)
    if actual_gated != case["expect_gated"]:
        problems.append(f"gate classification: got {actual_gated}, expected {case['expect_gated']}")

    before = None
    worker_id = resolved_args.get("worker_id")
    if worker_id:
        w = core._find_worker(workers, worker_id)
        before = dict(w) if w else None

    call_counter = [0]
    approve_fn = make_approve_fn(case["decision"], call_counter)
    result = core.handle_tool_call(case["tool"], resolved_args, approve_fn=approve_fn)

    approve_called = call_counter[0] > 0
    if approve_called != case["expect_approve_called"]:
        problems.append(f"approver invocation: got called={approve_called}, expected {case['expect_approve_called']}")

    if result.get("status") != case["expect_status"]:
        problems.append(f"status: got '{result.get('status')}', expected '{case['expect_status']}'")

    for post in case.get("post_checks", []):
        ok, msg = check_post(post, before)
        if not ok:
            problems.append(f"post_check {post['type']}: {msg}")

    return len(problems) == 0, problems


def main() -> None:
    shutil.copy(DATA_PATH, PRISTINE_BACKUP)
    cases = json.loads((TESTS_DIR / "test_cases.json").read_text())

    passed = 0
    failures = []

    try:
        for case in cases:
            shutil.copy(PRISTINE_BACKUP, DATA_PATH)  # isolate each case
            ok, problems = run_case(case)
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {case['id']}: {case['description']}")
            if not ok:
                failures.append((case["id"], problems))
                for p in problems:
                    print(f"        - {p}")
            else:
                passed += 1
    finally:
        shutil.copy(PRISTINE_BACKUP, DATA_PATH)  # restore your real data
        PRISTINE_BACKUP.unlink(missing_ok=True)

    total = len(cases)
    print()
    print("=" * 60)
    print(f"Result: {passed}/{total} passed ({100 * passed / total:.1f}%)")
    if failures:
        print("\nFailed cases:")
        for case_id, problems in failures:
            print(f"  {case_id}: {'; '.join(problems)}")
    print("=" * 60)


if __name__ == "__main__":
    main()