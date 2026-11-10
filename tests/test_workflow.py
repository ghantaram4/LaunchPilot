import json
import subprocess
import sys

import pytest

from conftest import FakeProvider, FakeRetriever
from launchpilot.facts import deterministic_review, fact_card
from launchpilot.models import FORMATS, Handoff
from launchpilot.service import Service
from launchpilot.storage import Store
from launchpilot.workflow import read_state


def test_complete_four_consistent_formats_with_real_tool_dispatch(store, docs, execute):
    cid = store.create(docs, consent=True, demo=True)
    state = execute(store, cid)
    assert state["status"] == "awaiting_human_review"
    assert set(state["drafts"]) == set(FORMATS)
    assert FakeRetriever.calls == 1
    assert FakeProvider.calls == ["research", "plan", "draft", "review:0"]
    assert not deterministic_review(state["drafts"], state["facts"], docs, state["bundle"], True)
    card = fact_card(state["facts"])
    assert all(text.count(card) == (3 if key == "ads" else 1) for key, text in state["drafts"].items())
    assert Service(store).working(cid)["approved"] is None
    with pytest.raises(Handoff, match="separately approved"):
        Service(store).export_bytes(cid)


@pytest.mark.parametrize("kind", ["missing", "conflicting"])
def test_essential_clarification_persists_and_resumes_without_regeneration(store, docs, execute, kind):
    if kind == "missing":
        for doc in docs:
            doc["text"] = "\n".join(line for line in doc["text"].splitlines() if not line.startswith("venue:"))
    else:
        docs[1]["text"] = docs[1]["text"].replace("date: 2027-02-20", "date: 2027-02-21")
    cid = store.create(docs, consent=True, demo=True)
    state = execute(store, cid)
    assert state["status"] == "clarification"
    field = "venue" if kind == "missing" else "date"
    assert field in [q["key"] for q in state["questions"]]
    assert FakeProvider.calls == ["research", "plan"]
    restarted = Store(store.root)
    assert read_state(restarted, cid)["questions"] == state["questions"]
    assert execute(restarted, cid)["status"] == "clarification"
    state = execute(restarted, cid, {field: "Innovation Studio, Aster College, Fictional City" if kind == "missing" else "2027-02-20"})
    assert state["status"] == "awaiting_human_review"
    assert state["facts"][field]["source_ids"][0].startswith("human:")
    assert FakeProvider.calls == ["research", "plan", "draft", "review:0"]


def test_invalid_clarification_is_not_accepted(store, docs, execute):
    for doc in docs:
        doc["text"] = doc["text"].replace("date: 2027-02-20", "date: TBD")
    cid = store.create(docs, consent=True)
    execute(store, cid)
    state = execute(store, cid, {"date": "2027-99-50"})
    assert state["status"] == "clarification"
    assert "date" not in state["facts"]
    assert FakeProvider.calls == ["research", "plan"]


@pytest.mark.parametrize("kind", ["retrieval", "provider", "malformed"])
def test_failure_is_disclosed_and_retry_only_failed_stage(store, docs, execute, kind):
    if kind == "retrieval":
        FakeRetriever.fail = True
    elif kind == "provider":
        FakeProvider.fail_stage = "draft"
    else:
        FakeProvider.malformed_stage = "draft"
    cid = store.create(docs, consent=True)
    state = execute(store, cid)
    assert state["status"] == "handoff"
    assert state["failure"]["kind"] == ("malformed_output" if kind == "malformed" else kind)
    assert state["failure"]["message"]
    calls = FakeProvider.calls.copy()
    assert execute(Store(store.root), cid)["status"] == "handoff"
    assert FakeProvider.calls == calls
    FakeRetriever.fail = False
    FakeProvider.fail_stage = None
    FakeProvider.malformed_stage = None
    state = execute(Store(store.root), cid, "retry")
    assert state["status"] == "awaiting_human_review"
    assert FakeProvider.calls.count("research") == 1
    assert FakeProvider.calls.count("plan") == 1


def test_one_revision_only_unresolved_issues_handed_to_human(store, docs, execute):
    FakeProvider.issues = [{"format": "blog", "severity": "warning", "detail": "Human should consider a clearer opening."}]
    cid = store.create(docs, consent=True)
    state = execute(store, cid)
    assert state["revision_count"] == 1 and len(state["review_history"]) == 2
    assert FakeProvider.calls == ["research", "plan", "draft", "review:0", "revision:1", "review:1"]
    service = Service(store)
    with pytest.raises(Handoff, match="resolution"):
        service.approve(cid, expected_version=1, reviewed=True)
    service.approve(cid, expected_version=1, reviewed=True, note="I reviewed the opening and accept its tone.")
    assert service.working(cid)["export_approved"] is None


def test_restart_preserves_approvals_and_edit_invalidates_export(store, docs, execute):
    cid = store.create(docs, consent=True, demo=True)
    execute(store, cid)
    service = Service(store)
    with pytest.raises(Handoff):
        service.approve_export(cid, expected_version=1, explicit=True)
    service.approve(cid, expected_version=1, reviewed=True)
    with pytest.raises(Handoff):
        service.export_bytes(cid)
    service.approve_export(cid, expected_version=1, explicit=True)
    assert b"FICTIONAL DEMO" in service.export_bytes(cid)
    # Fresh interpreter reconstructs SQLite checkpoint and approval stores; no provider factory/network.
    code = "from pathlib import Path; from launchpilot.storage import Store; from launchpilot.service import Service; import json; s=Service(Store(Path(__import__('sys').argv[1]))); cid=__import__('sys').argv[2]; print(json.dumps({'status':s.state(cid)['status'],'approved':bool(s.working(cid)['approved']),'export':bool(s.working(cid)['export_approved'])}))"
    result = subprocess.run([sys.executable, "-c", code, str(store.root), cid], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {"status": "awaiting_human_review", "approved": True, "export": True}
    before = FakeProvider.calls.copy()
    execute(Store(store.root), cid)
    assert FakeProvider.calls == before
    work = service.working(cid)
    edited = {**work["drafts"], "linkedin": work["drafts"]["linkedin"] + "\nBring your curiosity."}
    service.edit(cid, edited, 1)
    work = Service(Store(store.root)).working(cid)
    assert work["version"] == 2 and work["approved"] is None and work["export_approved"] is None
    with pytest.raises(Handoff):
        service.export_bytes(cid)


def test_critical_fact_edits_block_approval(store, docs, execute):
    cid = store.create(docs, consent=True)
    execute(store, cid)
    service = Service(store)
    work = service.working(cid)
    drafts = {**work["drafts"], "email": work["drafts"]["email"].replace("2027-02-20", "2027-02-21")}
    service.edit(cid, drafts, 1)
    with pytest.raises(Handoff, match="Critical fact checks"):
        service.approve(cid, expected_version=2, reviewed=True, note="I checked this edited content.")


def test_no_consent_no_campaign_writes(store, docs):
    with pytest.raises(Handoff, match="consent"):
        store.create(docs, consent=False)
    assert store.list() == [] and list(store.campaigns.iterdir()) == []


def test_additional_inspection_persists_missed_claim_for_human_resolution(store, docs, execute):
    cid = store.create(docs, consent=True)
    execute(store, cid)
    service = Service(store)
    issue = {"format": "blog", "severity": "blocking", "detail": "An institutional belief is not supported by the brief. Remove it or provide confirmation."}
    service.record_inspection(cid, [issue])
    assert read_state(Store(store.root), cid)["review_history"][-1]["additional_inspection"] == [issue]
    with pytest.raises(Handoff, match="resolution"):
        service.approve(cid, expected_version=1, reviewed=True)
    assert service.working(cid)["approved"] is None


def test_malformed_retrieval_arguments_handoff_at_research_and_recover(store, docs):
    from launchpilot.workflow import run
    class BadArgsProvider(FakeProvider):
        bad = True
        def call(self, stage, messages, **kwargs):
            result = super().call(stage, messages, **kwargs)
            if stage == "research" and self.bad:
                result.tool_calls[0]["args"] = {"query": 42}
            return result
    cid = store.create(docs, consent=True)
    state = run(store, cid, provider_factory=BadArgsProvider, retriever_factory=FakeRetriever)
    assert state["failure"]["kind"] == "malformed_output" and state["retry_node"] == "research"
    assert FakeRetriever.calls == 0
    BadArgsProvider.bad = False
    state = run(store, cid, response="retry", provider_factory=BadArgsProvider, retriever_factory=FakeRetriever)
    assert state["status"] == "awaiting_human_review" and FakeRetriever.calls == 1
