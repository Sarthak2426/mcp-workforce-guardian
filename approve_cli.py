import time

import approval_broker


def describe(request: dict) -> str:
    tool = request["tool"]
    args = request["args"]
    if tool == "delete_worker":
        return f"DELETE worker '{args.get('worker_id')}' — this is permanent."
    if tool == "terminate_worker":
        return f"TERMINATE worker '{args.get('worker_id')}'."
    if tool == "update_worker":
        return f"UPDATE worker '{args.get('worker_id')}' — sensitive fields: {args.get('updates')}"
    if tool == "log_hourly_output":
        return (f"LOG HOURLY OUTPUT for '{args.get('worker_id')}': "
                f"{args.get('parts_made')} made, {args.get('rejected_parts')} rejected.")
    return f"{tool}({args})"


def main() -> None:
    print("=" * 60)
    print("Workforce Guardian — human approval console")
    print("Type a request's id to resolve it, in whatever order you like.")
    print("=" * 60)
    while True:
        pending = approval_broker.list_pending()
        if not pending:
            time.sleep(1)
            continue

        print(f"\n{len(pending)} pending request(s):")
        for request in pending:
            print(f"  [{request['id']}] {describe(request)}  (requested {request['requested_at']})")

        choice = input("\nEnter an id to resolve (Enter to refresh the list): ").strip()
        if not choice:
            continue

        matching = next((r for r in pending if r["id"] == choice), None)
        if matching is None:
            print("  No pending request with that id -- try again.")
            continue

        decision = input(f"  Approve [{matching['id']}]? [y/N]: ").strip().lower()
        approved = decision == "y"
        reason = "" if approved else "Denied via approve_cli.py"
        approval_broker.resolve(matching["id"], approved, reason)
        print(f"  -> {'APPROVED' if approved else 'DENIED'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")