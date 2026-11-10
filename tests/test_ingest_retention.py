import io
import time

import pytest
from pypdf import PdfWriter

from launchpilot.facts import resolve
from launchpilot.ingest import calendar, extract
from launchpilot.models import Handoff
from launchpilot.provider import Budget, NebiusProvider


@pytest.mark.parametrize("raw", [b"wrong,headers\na,b\n", b"event_name,date\na,b,c\n", b"event_name,event_name\na,b\n", b"event_name,date\n\"unclosed,b", b"\xff\xfe"])
def test_bad_calendars_disclosed(raw):
    with pytest.raises(Handoff, match="calendar|UTF-8"):
        calendar(raw)


def test_scanned_corrupt_and_empty_briefs_disclosed():
    pdf = PdfWriter()
    pdf.add_blank_page(400, 400)
    stream = io.BytesIO()
    pdf.write(stream)
    for name, raw in [("bad.pdf", b"not pdf"), ("scan.pdf", stream.getvalue()), ("empty.txt", b"")]:
        with pytest.raises(Handoff, match="brief|Brief"):
            extract(name, raw, "calendar.csv", b"event_name\nDemo\n")


def test_text_based_pdf_extraction_preserves_page_metadata():
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    page = writer.add_blank_page(600, 800)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 40 740 Td (FICTIONAL DEMO college workshop event brief) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    docs = extract("fictional.pdf", output.getvalue(), "fictional.csv", b"event_name\nFictional workshop\n")
    assert docs[0]["page"] == 1 and docs[0]["filename"] == "fictional.pdf"
    assert "FICTIONAL DEMO college workshop" in docs[0]["text"] and len(docs[0]["sha256"]) == 64


def test_unsupported_model_facts_cannot_replace_sources(docs):
    for doc in docs:
        doc["text"] = "\n".join(line for line in doc["text"].splitlines() if not line.startswith("price:"))
    facts, questions = resolve(docs, {"facts": {"price": {"value": "USD 999", "source_ids": ["brief:p1"], "quote": "Made up price"}}, "questions": []}, {})
    assert "price" not in facts and any(q["key"] == "price" for q in questions)


def test_case_sensitive_registration_paths_conflict(docs):
    docs[1]["text"] = docs[1]["text"].replace("aster-ideas-demo", "ASTER-ideas-demo")
    _, questions = resolve(docs, {"facts": {}, "questions": []}, {})
    assert any(q["key"] == "registration_url" for q in questions)


def test_cleanup_removes_campaign_uploads_embeddings_checkpoints_but_not_exports(store, docs, tmp_path):
    cid = store.create(docs, consent=True, raw_files=[("brief.txt", b"fictional source")])
    path = store.path(cid)
    (path / "chroma").mkdir()
    (path / "chroma/embeddings.bin").write_bytes(b"fictional vector")
    (path / "checkpoints.sqlite").write_bytes(b"retained checkpoint")
    export = tmp_path / "user-download.md"
    export.write_text("User-owned export")
    active = store.create(docs, consent=True)
    with store.registry() as conn:
        conn.execute("UPDATE campaigns SET expires=? WHERE id=?", (time.time() - 1, cid))
    assert store.cleanup()["removed"] == 1
    assert not path.exists() and export.exists() and store.path(active).exists()
    with pytest.raises(Handoff, match="expired"):
        store.get(cid, "docs")


def test_attempt_and_time_limits_prevent_provider_start(store, docs, monkeypatch):
    cid = store.create(docs, consent=True)
    store.set(cid, "max_attempts", 0)
    monkeypatch.setattr("launchpilot.provider.credential", lambda: "offline-test-key")
    monkeypatch.setattr("launchpilot.provider.subprocess.Popen", lambda *a, **k: pytest.fail("Provider must not start"))
    from langchain_core.messages import HumanMessage
    budget = Budget(store, cid)
    with pytest.raises(Handoff, match="limit"):
        NebiusProvider(store, cid, budget).call("test", [HumanMessage(content="fictional")])
    budget.finish()
    store.set(cid, "max_attempts", 8)
    store.set(cid, "max_seconds", 0)
    budget = Budget(store, cid)
    with pytest.raises(Handoff, match="limit"):
        NebiusProvider(store, cid, budget).call("test", [HumanMessage(content="fictional")])
    budget.finish()
