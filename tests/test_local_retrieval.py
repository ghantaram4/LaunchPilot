import pytest

from launchpilot.retrieval import Retriever, chunks, embedding_model


@pytest.mark.integration
def test_real_tokenizer_chroma_persistence_isolation_and_cleanup(store, docs):
    model = embedding_model()
    long_docs = [{**docs[0], "text": ("A campus creative workshop: idea mapping and peer discussion. " * 220)}]
    pieces = chunks(long_docs, model)
    assert len(pieces) > 2
    assert all(len(model.tokenizer.encode(c["text"], add_special_tokens=True)) < model.max_seq_length for c in pieces)
    assert pieces[1]["metadata"]["start_char"] < pieces[0]["metadata"]["end_char"]
    cid = store.create(docs, consent=True)
    hits = Retriever(store, cid).search("confirmed event date venue price registration")
    assert hits and all(h["source_id"] in {"brief:p1", "calendar:r2"} for h in hits)
    assert (store.path(cid) / "chroma/chroma.sqlite3").exists()
    restarted = Retriever(store, cid).search("confirmed event date venue price registration")
    assert [h["chunk_id"] for h in restarted] == [h["chunk_id"] for h in hits]
    other = store.create([{**docs[0], "text": "Unique second campaign: violet lantern workshop."}], consent=True)
    other_hits = Retriever(store, other).search("violet")
    assert all("violet" in h["text"] and "2027-02-20" not in h["text"] for h in other_hits)
    with store.registry() as conn:
        conn.execute("UPDATE campaigns SET expires=0")
    assert store.cleanup()["removed"] == 2
    assert list(store.campaigns.iterdir()) == []
