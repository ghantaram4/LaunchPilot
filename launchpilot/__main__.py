import argparse
import json
from pathlib import Path

from .config import DATA, ROOT
from .facts import deterministic_review
from .ingest import extract
from .models import Handoff
from .service import Service
from .storage import Store


def live_summary(service, cid):
    state = service.state(cid)
    work = service.working(cid)
    calls = service.store.calls(cid)
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    unknown_usage = 0
    for call in calls:
        usage = json.loads(call["usage"]) if call["usage"] else None
        if usage:
            for key in totals:
                totals[key] += usage.get(key, 0)
        else:
            unknown_usage += 1
    issues = deterministic_review(state["drafts"], state["facts"], service.store.get(cid, "docs"),
                                  state["bundle"], True) if state.get("drafts") else None
    return {"campaign_id": cid, "fictional_only": True, "status": state.get("status"),
            "provider_attempts": len(calls), "active_seconds": service.store.get(cid, "active_spent"),
            "provider_seconds": sum(c["elapsed"] for c in calls), "usage": totals,
            "attempts_without_usage": unknown_usage, "revision_count": state.get("revision_count", 0),
            "four_formats": len(state.get("drafts", {})) == 4, "critical_fact_issues": issues,
            "latest_review_issues": state.get("review_history", [{}])[-1].get("issues", []),
            "pending_questions": state.get("questions", []), "failure": state.get("failure"),
            "content_approved": bool(work and work["approved"]),
            "export_approved": bool(work and work["export_approved"]), "calls": calls}


def main():
    parser = argparse.ArgumentParser(description="LaunchPilot local operations; no sending or publishing.")
    parser.add_argument("command", choices=["prepare-model", "cleanup", "live-demo", "live-status"])
    parser.add_argument("--data-dir", type=Path, default=DATA)
    args = parser.parse_args()
    if args.command == "prepare-model":
        from .retrieval import embedding_model
        model = embedding_model()
        print(json.dumps({"model": "sentence-transformers/all-MiniLM-L6-v2", "input_limit": model.max_seq_length,
                          "dimensions": model.get_embedding_dimension(), "ready": True}))
        return
    service = Service(Store(args.data_dir))
    service.clean()
    if args.command == "cleanup":
        print(json.dumps(service.store.cleanup()))
        return
    if args.command == "live-demo":
        # Permanent, source-free marker prevents silently starting another task-authorized workflow.
        marker = ROOT / ".authorized-live-workflow-used"
        with service.store.lock:
            try:
                with marker.open("x", encoding="utf-8") as target:
                    target.write("The task-authorized fictional live workflow has been consumed.\n")
            except FileExistsError:
                raise Handoff("live_guard", "The one task-authorized live workflow has already been started. Use live-status or resume its saved campaign in the UI; do not start another.", False) from None
            name, cal_name = "FICTIONAL_event_brief.txt", "FICTIONAL_event_calendar.csv"
            brief, cal = (ROOT / "demo" / name).read_bytes(), (ROOT / "demo" / cal_name).read_bytes()
            docs = extract(name, brief, cal_name, cal)
            # These are the bundled fictional files only, with the fixed Nebius destination.
            cid = service.store.create(docs, consent=True, demo=True, raw_files=[(name, brief), (cal_name, cal)])
            service.store.set(cid, "authorized_live_demo", True)
        service.run(cid, callback=lambda stage: print(f"Stage: {stage}", flush=True))
    else:
        ids = [r["id"] for r in service.store.list() if service.store.get(r["id"], "authorized_live_demo")]
        if not ids:
            raise Handoff("live_status", "No retained task-authorized live campaign is available.", False)
        cid = ids[0]
    result = live_summary(service, cid)
    # Report is campaign-owned and expires with the rest of the data.
    (service.store.path(cid) / "live_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Handoff as exc:
        print(json.dumps({"error": exc.kind, "message": exc.message}))
        raise SystemExit(1) from None
