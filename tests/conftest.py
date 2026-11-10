import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from launchpilot.config import ROOT
from launchpilot.ingest import candidates, extract
from launchpilot.models import Handoff
from launchpilot.provider import NebiusProvider
from launchpilot.storage import Store


@pytest.fixture
def docs():
    return extract("FICTIONAL_event_brief.txt", (ROOT / "demo/FICTIONAL_event_brief.txt").read_bytes(),
                   "FICTIONAL_event_calendar.csv", (ROOT / "demo/FICTIONAL_event_calendar.csv").read_bytes())


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "data")


class FakeProvider:
    calls = []
    fail_stage = None
    issues = []
    malformed_stage = None

    def __init__(self, store, cid, budget):
        self.store, self.cid = store, cid

    def invalidate(self, stage):
        pass

    def call(self, stage, messages, **kwargs):
        self.calls.append(stage)
        if stage == self.fail_stage:
            raise Handoff("provider", "Simulated provider failure; completed stages retained.")
        if stage == self.malformed_stage:
            return AIMessage(content="not JSON")
        if stage == "research":
            assert kwargs.get("tools") and kwargs["tools"][0].name == "retrieve_sources"
            return AIMessage(content="", tool_calls=[{"name": "retrieve_sources", "args": {"query": "event date time venue price registration audience tone"}, "id": "call_offline"}])
        if stage == "plan":
            assert any(m.type == "tool" for m in messages), "Planning must receive a real tool result"
            facts = {key: items[0] for key, items in candidates(self.store.get(self.cid, "docs")).items() if items}
            return AIMessage(content=json.dumps({"facts": facts, "questions": [], "approach": "Invite students to the supported creative workshop."}))
        if stage.startswith("review:"):
            return AIMessage(content=json.dumps({"issues": self.issues, "summary": "Offline scripted review; human review required."}))
        draft = {"text": "Explore campus challenges with guided idea mapping, small-group discussion and a peer feedback circle. Bring your curiosity.", "source_ids": ["brief:p1"]}
        return AIMessage(content=json.dumps({"linkedin": draft, "email": {**draft, "text": "Subject: Explore campus ideas\n\n" + draft["text"]},
                                            "blog": {**draft, "text": "Campus ideas, explored together\n\n" + draft["text"]}, "ads": [draft] * 3}))

    structured = NebiusProvider.structured


class FakeRetriever:
    fail = False
    calls = 0

    def __init__(self, store, cid):
        self.store, self.cid = store, cid

    def tool(self):
        @tool
        def retrieve_sources(query: str) -> str:
            """Retrieve local offline fixture source evidence."""
            FakeRetriever.calls += 1
            if FakeRetriever.fail:
                raise Handoff("retrieval", "Simulated retrieval unavailable; no facts guessed.")
            doc = self.store.get(self.cid, "docs")[0]
            return json.dumps({"matches": [{"source_id": doc["id"], "chunk_id": "offline:c0", "text": doc["text"],
                                            "filename": doc["filename"], "page": 1, "row": 0}],
                               "source_audit": self.store.get(self.cid, "docs")})
        return retrieve_sources


@pytest.fixture(autouse=True)
def reset_fakes():
    FakeProvider.calls = []
    FakeProvider.fail_stage = None
    FakeProvider.issues = []
    FakeProvider.malformed_stage = None
    FakeRetriever.fail = False
    FakeRetriever.calls = 0


@pytest.fixture
def execute():
    from launchpilot.workflow import run
    def impl(store, cid, response=None):
        return run(store, cid, response=response, provider_factory=FakeProvider, retriever_factory=FakeRetriever)
    return impl
