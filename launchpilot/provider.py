import hashlib
import json
import subprocess
import sys
import time

from langchain_core.messages import message_to_dict, messages_from_dict
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ValidationError

from .config import ROOT, credential
from .diagnostics import failure_report, log_failure, runtime_context
from .models import Handoff


class Budget:
    def __init__(self, store, cid):
        self.store, self.cid = store, cid
        self.started = time.monotonic()
        previous = store.get(cid, "run_started")
        self.base = store.get(cid, "active_spent")
        if previous is not None:
            # An interrupted process cannot prove how much work completed. Charge elapsed wall time conservatively.
            self.base += max(0, time.time() - previous)
            store.set(cid, "active_spent", self.base)
        store.set(cid, "run_started", time.time())

    def remaining(self):
        return self.store.get(self.cid, "max_seconds") - self.base - (time.monotonic() - self.started)

    def finish(self):
        self.store.set(self.cid, "active_spent", self.base + time.monotonic() - self.started)
        self.store.set(self.cid, "run_started", None)


class NebiusProvider:
    def __init__(self, store, cid, budget):
        self.store, self.cid, self.budget = store, cid, budget

    def invalidate(self, stage):
        with self.store.db(self.cid) as conn:
            conn.execute("UPDATE calls SET status='malformed',error='Output failed schema validation' WHERE stage=? AND status='success'", (stage,))

    def call(self, stage, messages, *, tools=None, json_mode=False, max_tokens=3500):
        if not self.store.get(self.cid, "consent")["accepted"]:
            raise Handoff("consent", "Consent is required.", False)
        payload = {"messages": [message_to_dict(m) for m in messages],
                   "tools": [convert_to_openai_tool(t) for t in tools] if tools else [],
                   "json_mode": json_mode, "max_tokens": max_tokens}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.store.db(self.cid) as conn:
            cached = conn.execute("SELECT response FROM calls WHERE stage=? AND input_hash=? AND status='success' ORDER BY id DESC LIMIT 1", (stage, digest)).fetchone()
            uncertain = conn.execute("SELECT id FROM calls WHERE stage=? AND input_hash=? AND status='inflight'", (stage, digest)).fetchone()
        if cached:
            return messages_from_dict([json.loads(cached[0])])[0]
        if uncertain:
            raise Handoff("uncertain_provider", "A provider request was interrupted and its completion is unknown. Explicitly acknowledge a possible duplicate charge before retrying this stage.")
        try:
            key = credential()
        except RuntimeError as exc:
            raise Handoff("provider_configuration", str(exc)) from None
        for retry in range(2):
            remaining = self.budget.remaining()
            with self.store.db(self.cid) as conn:
                attempts = conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
                if attempts >= self.store.get(self.cid, "max_attempts") or remaining < 2:
                    raise Handoff("budget", "Provider attempt or active-time limit reached. Completed work is retained; no further generation is authorized for this campaign.", False)
                timeout = min(40.0, remaining - 0.5)
                cursor = conn.execute("INSERT INTO calls(stage,input_hash,status,started) VALUES (?,?,'inflight',?)", (stage, digest, time.time()))
                call_id = cursor.lastrowid
            started = time.monotonic()
            request = {**payload, "api_key": key, "timeout": timeout}
            try:
                child = subprocess.Popen([sys.executable, "-m", "launchpilot.worker"], cwd=ROOT,
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                try:
                    output, _ = child.communicate(json.dumps(request), timeout=timeout)
                    answer = json.loads(output)
                except subprocess.TimeoutExpired as exc:
                    child.kill()
                    child.communicate()
                    answer = {"ok": False, "kind": "timeout", "transient": True,
                              "diagnostics": failure_report(exc, credential_loaded=bool(key))}
                except (ValueError, OSError) as exc:
                    answer = {"ok": False, "kind": "worker_output", "transient": False,
                              "diagnostics": failure_report(exc, credential_loaded=bool(key))}
            except OSError as exc:
                answer = {"ok": False, "kind": "worker_start", "transient": False,
                          "diagnostics": failure_report(exc, credential_loaded=bool(key))}
            elapsed = time.monotonic() - started
            ok = answer.get("ok") is True
            with self.store.db(self.cid) as conn:
                conn.execute("UPDATE calls SET status=?,elapsed=?,response=?,usage=?,error=? WHERE id=?",
                             ("success" if ok else "failed", elapsed,
                              json.dumps(answer["message"]) if ok else None,
                              json.dumps(answer.get("usage")), None if ok else answer.get("kind", "provider"), call_id))
            if ok:
                return messages_from_dict([answer["message"]])[0]
            diagnostic = answer.get("diagnostics") or {"exception_chain": [], "runtime": runtime_context(credential_loaded=bool(key))}
            log_failure(self.store, self.cid, call_id, stage, diagnostic)
            if answer.get("transient") and retry == 0 and self.budget.remaining() > 3:
                time.sleep(0.5)
                continue
            raise Handoff("provider", f"Nebius request failed ({answer.get('kind', 'provider')}). This stage is paused; completed stages are retained. Retry explicitly when the provider is available.")

    def structured(self, stage, messages, schema, *, max_tokens=3500):
        result = self.call(stage, messages, json_mode=True, max_tokens=max_tokens)
        try:
            if not isinstance(result.content, str):
                raise ValueError()
            return schema.model_validate_json(result.content).model_dump()
        except (ValidationError, ValueError, TypeError):
            self.invalidate(stage)
            raise Handoff("malformed_output", f"The {stage} response did not match its required JSON schema. No malformed content was accepted. Retry this stage explicitly.") from None


def structured_prompt(schema) -> str:
    return "Return only a JSON object matching this schema exactly, with no markdown fences:\n" + json.dumps(schema.model_json_schema())
