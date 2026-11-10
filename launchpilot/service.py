import hashlib
import json
import time

from .facts import deterministic_review
from .models import FORMATS, Handoff, Issue
from .storage import Store
from .workflow import config, graph_session, read_state, run


def digest(drafts):
    return hashlib.sha256(json.dumps(drafts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Service:
    def __init__(self, store=None):
        self.store = store or Store()

    def clean(self):
        result = self.store.cleanup()
        if result["errors"]:
            raise Handoff("retention", " ".join(result["errors"]))
        return result

    def state(self, cid):
        self.clean()
        return read_state(self.store, cid)

    def run(self, cid, **kwargs):
        self.clean()
        return run(self.store, cid, **kwargs)

    def working(self, cid):
        state = self.state(cid)
        if not state.get("drafts") or state.get("status") != "awaiting_human_review":
            return None
        with self.store.lock:
            work = self.store.work(cid)
            if work is None:
                work = {"drafts": state["drafts"], "version": 1, "approved": None,
                        "export_approved": None, "edited": False, "audit": []}
                self.store.save_work(cid, work)
        return work

    def issues(self, cid, work=None):
        state = self.state(cid)
        work = work or self.working(cid)
        if not work:
            return []
        return deterministic_review(work["drafts"], state["facts"], self.store.get(cid, "docs"),
                                    demo=self.store.get(cid, "demo"))

    def edit(self, cid, drafts, expected_version):
        self.clean()
        if set(drafts) != set(FORMATS) or any(not isinstance(v, str) or not v.strip() or len(v) > 30000 for v in drafts.values()):
            raise Handoff("edit", "Supply nonempty text for all four formats (up to 30,000 characters each).", False)
        with self.store.lock:
            work = self.working(cid)
            if work["version"] != expected_version:
                raise Handoff("edit", "Drafts changed in another session. Reload before saving.")
            if drafts != work["drafts"]:
                work.update(drafts=drafts, version=work["version"] + 1, approved=None, export_approved=None, edited=True)
                work["audit"].append({"action": "edit_invalidated_approvals", "at": time.time(), "version": work["version"]})
                self.store.save_work(cid, work)
            return work

    def record_inspection(self, cid, issues):
        """Persist additional inspection findings without representing them as model or human approval."""
        self.clean()
        checked = [Issue.model_validate(issue).model_dump() for issue in issues]
        with self.store.lock:
            with graph_session(self.store, cid) as graph:
                state = graph.get_state(config(cid)).values
                if state.get("status") != "awaiting_human_review":
                    raise Handoff("review", "Inspection findings can be added after the automated workflow completes.", False)
                history = state["review_history"]
                history[-1].setdefault("additional_inspection", []).extend(checked)
                history[-1]["issues"].extend(checked)
                graph.update_state(config(cid), {"review_history": history}, as_node="finish")
            work = self.working(cid)
            work["approved"] = None
            work["export_approved"] = None
            work["audit"].append({"action": "additional_inspection", "at": time.time(), "issues": checked})
            self.store.save_work(cid, work)

    def approve(self, cid, *, expected_version, reviewed, note=""):
        self.clean()
        with self.store.lock:
            state = self.state(cid)
            work = self.working(cid)
            if state.get("status") != "awaiting_human_review":
                raise Handoff("approval", "Finish generation/review or resolve the handoff before approving.", False)
            if not reviewed or work["version"] != expected_version:
                raise Handoff("approval", "Explicitly review the current version before approval.", False)
            if self.issues(cid, work):
                raise Handoff("approval", "Critical fact checks are blocking approval. Repair the drafts and review again.", False)
            issues = state["review_history"][-1]["issues"] if state.get("review_history") else []
            if (issues or work["edited"]) and len(note.strip()) < 12:
                raise Handoff("approval", "Record your human resolution of review issues or edited-content review (at least 12 characters).", False)
            work["approved"] = {"digest": digest(work["drafts"]), "version": work["version"],
                                "at": time.time(), "note": note, "human_reviewed": True}
            work["export_approved"] = None
            work["audit"].append({"action": "content_approved", **work["approved"]})
            self.store.save_work(cid, work)

    def approve_export(self, cid, *, expected_version, explicit):
        self.clean()
        with self.store.lock:
            work = self.working(cid)
            if not work or not explicit or expected_version != work["version"] or not work["approved"] or work["approved"]["digest"] != digest(work["drafts"]):
                raise Handoff("export", "Separate explicit export approval and current content approval are required.", False)
            if self.issues(cid, work):
                raise Handoff("export", "Critical fact checks block export.", False)
            work["export_approved"] = {"digest": digest(work["drafts"]), "at": time.time(), "version": work["version"]}
            work["audit"].append({"action": "export_approved", **work["export_approved"]})
            self.store.save_work(cid, work)

    def export_bytes(self, cid):
        self.clean()
        with self.store.lock:
            work = self.working(cid)
            current = digest(work["drafts"]) if work else None
            if not work or not work["approved"] or not work["export_approved"] or any(work[k]["digest"] != current for k in ("approved", "export_approved")):
                raise Handoff("export", "Export has not been separately approved for this version.", False)
            state = self.state(cid)
            parts = ["# LaunchPilot campaign", f"Version: {work['version']}",
                     "Human approved. Model review is fallible; source references are included below."]
            for key in FORMATS:
                parts.extend([f"## {key.title()}", work["drafts"][key]])
            parts.append("## Supporting facts")
            for key, fact in state["facts"].items():
                parts.append(f"- {key}: {fact['value']} | Sources: {', '.join(fact['source_ids'])} | Quote: {fact['quote']}")
            parts.extend(["## Human approval note", work["approved"]["note"] or "Reviewed without outstanding issues.",
                          "## Review history", json.dumps(state["review_history"], ensure_ascii=False, indent=2)])
            return "\n\n".join(parts).encode("utf-8")
