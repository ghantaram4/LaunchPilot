import json
import subprocess

import pytest
from langchain_core.messages import AIMessage, HumanMessage, message_to_dict

from launchpilot.models import Handoff
from launchpilot.provider import Budget, NebiusProvider


def test_transient_retry_is_bounded_and_success_cache_survives_restart(store, docs, monkeypatch):
    cid = store.create(docs, consent=True)
    monkeypatch.setattr("launchpilot.provider.credential", lambda: "private-offline-placeholder")
    requests = []
    class Child:
        def __init__(self, *args, **kwargs):
            assert "private-offline-placeholder" not in str(args), "Never put credentials in argv"
        def communicate(self, request=None, timeout=None):
            requests.append(json.loads(request))
            if len(requests) == 1:
                return json.dumps({"ok": False, "kind": "http_429", "transient": True}), ""
            return json.dumps({"ok": True, "message": message_to_dict(AIMessage(content="cached completed draft")),
                               "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}), ""
    monkeypatch.setattr("launchpilot.provider.subprocess.Popen", Child)
    budget = Budget(store, cid)
    first = NebiusProvider(store, cid, budget).call("draft", [HumanMessage(content="fictional")])
    budget.finish()
    assert first.content == "cached completed draft" and len(requests) == 2
    budget = Budget(store, cid)
    second = NebiusProvider(store, cid, budget).call("draft", [HumanMessage(content="fictional")])
    budget.finish()
    assert second.content == first.content and len(requests) == 2
    assert [c["status"] for c in store.calls(cid)] == ["failed", "success"]
    db_bytes = (store.path(cid) / "application.sqlite").read_bytes()
    assert b"private-offline-placeholder" not in db_bytes


def test_nontransient_provider_error_has_no_automatic_retry(store, docs, monkeypatch):
    cid = store.create(docs, consent=True)
    monkeypatch.setattr("launchpilot.provider.credential", lambda: "offline-key")
    class Child:
        def __init__(self, *args, **kwargs):
            pass
        def communicate(self, *args, **kwargs):
            return json.dumps({"ok": False, "kind": "http_400", "transient": False}), ""
    monkeypatch.setattr("launchpilot.provider.subprocess.Popen", Child)
    budget = Budget(store, cid)
    with pytest.raises(Handoff, match="http_400"):
        NebiusProvider(store, cid, budget).call("draft", [HumanMessage(content="fictional")])
    budget.finish()
    assert len(store.calls(cid)) == 1


def test_hard_timeout_kills_child_and_never_exceeds_attempt_limit(store, docs, monkeypatch):
    cid = store.create(docs, consent=True)
    monkeypatch.setattr("launchpilot.provider.credential", lambda: "offline-key")
    store.set(cid, "max_attempts", 2)
    killed = []
    class Child:
        def __init__(self, *args, **kwargs):
            self.killed = False
        def communicate(self, request=None, timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired("offline", timeout)
            return "", ""
        def kill(self):
            self.killed = True
            killed.append(True)
    monkeypatch.setattr("launchpilot.provider.subprocess.Popen", Child)
    budget = Budget(store, cid)
    with pytest.raises(Handoff):
        NebiusProvider(store, cid, budget).call("draft", [HumanMessage(content="fictional")])
    with pytest.raises(Handoff, match="limit"):
        NebiusProvider(store, cid, budget).call("draft", [HumanMessage(content="fictional")])
    budget.finish()
    assert len(killed) == 2 and len(store.calls(cid)) == 2


def test_compatible_nebius_wire_settings_without_network():
    import httpx
    from launchpilot.config import MODEL
    from launchpilot.worker import make_model
    captured = []
    def handler(request):
        assert str(request.url) == "https://api.tokenfactory.nebius.com/v1/chat/completions"
        payload = json.loads(request.content)
        captured.append(payload)
        return httpx.Response(200, json={"id": "offline", "object": "chat.completion", "created": 1, "model": MODEL,
                              "choices": [{"index": 0, "message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}],
                              "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        model = make_model({"api_key": "offline-placeholder", "timeout": 2, "max_tokens": 123}, http_client=client)
        model.bind(response_format={"type": "json_object"}).invoke([HumanMessage(content="fictional")])
        model.bind_tools([{"type": "function", "function": {"name": "retrieve_sources", "description": "Search local sources", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}], tool_choice={"type": "function", "function": {"name": "retrieve_sources"}}, parallel_tool_calls=False).invoke([HumanMessage(content="fictional")])
    assert len(captured) == 2
    for payload in captured:
        assert payload["model"] == MODEL and payload["reasoning_effort"] == "low"
        assert payload["max_tokens"] == 123 and "max_completion_tokens" not in payload
        assert payload["temperature"] == 1
    assert captured[0]["response_format"] == {"type": "json_object"}
    assert captured[1]["tool_choice"]["function"]["name"] == "retrieve_sources"
    assert captured[1]["parallel_tool_calls"] is False


def test_uncertain_inflight_request_does_not_silently_repeat(store, docs, monkeypatch):
    cid = store.create(docs, consent=True)
    import hashlib
    from langchain_core.messages import message_to_dict
    messages = [HumanMessage(content="fictional")]
    payload = {"messages": [message_to_dict(m) for m in messages], "tools": [], "json_mode": False, "max_tokens": 3500}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    with store.db(cid) as conn:
        conn.execute("INSERT INTO calls(stage,input_hash,status,started) VALUES (?,?,'inflight',0)", ("draft", digest))
    monkeypatch.setattr("launchpilot.provider.subprocess.Popen", lambda *a, **k: pytest.fail("Uncertain request must wait for acknowledgement"))
    budget = Budget(store, cid)
    with pytest.raises(Handoff, match="duplicate charge"):
        NebiusProvider(store, cid, budget).call("draft", messages)
    budget.finish()
    assert len(store.calls(cid)) == 1
