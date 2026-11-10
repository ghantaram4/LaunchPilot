import gc
import json
from functools import lru_cache

from langchain_core.tools import tool

from .config import EMBED_MODEL
from .models import Handoff


@lru_cache(maxsize=1)
def embedding_model():
    from sentence_transformers import SentenceTransformer
    try:
        return SentenceTransformer(EMBED_MODEL, device="cpu", trust_remote_code=False)
    except Exception:
        raise Handoff("retrieval", "The local MiniLM embedding model could not load. Prepare the model cache and retry; no substitute embeddings were used.") from None


def chunks(docs: list[dict], model=None) -> list[dict]:
    model = model or embedding_model()
    tokenizer = model.tokenizer
    limit = min(int(model.max_seq_length), 256)
    payload = min(220, limit - tokenizer.num_special_tokens_to_add(pair=False) - 1)
    overlap = min(24, payload // 4)
    output = []
    for doc in docs:
        offsets = tokenizer(doc["text"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        for start in range(0, len(offsets), payload - overlap):
            end = min(start + payload, len(offsets))
            text = doc["text"][offsets[start][0]:offsets[end - 1][1]]
            size = len(tokenizer.encode(text, add_special_tokens=True))
            if size >= limit:
                raise Handoff("retrieval", "A source chunk exceeds the embedding tokenizer limit. Shorten the source.", False)
            output.append({"id": f"{doc['id']}:c{start}", "text": text, "metadata": {
                "source_id": doc["id"], "filename": doc["filename"], "page": doc["page"],
                "row": doc["row"], "sha256": doc["sha256"], "tokens": size,
                "start_char": offsets[start][0], "end_char": offsets[end - 1][1]}})
            if end == len(offsets):
                break
    if not output or len(output) > 400:
        raise Handoff("retrieval", "Brief/calendar is empty or too large for this MVP; use a focused event brief.", False)
    return output


class Retriever:
    def __init__(self, store, cid):
        self.store, self.cid = store, cid

    def search(self, query: str) -> list[dict]:
        client = None
        try:
            import chromadb
            from chromadb.config import Settings
            model = embedding_model()
            items = chunks(self.store.get(self.cid, "docs"), model)
            client = chromadb.PersistentClient(path=str(self.store.path(self.cid) / "chroma"),
                                             settings=Settings(anonymized_telemetry=False))
            collection = client.get_or_create_collection("event_sources", embedding_function=None,
                                                        metadata={"hnsw:space": "cosine"})
            if collection.count() != len(items):
                vectors = model.encode([c["text"] for c in items], normalize_embeddings=True).tolist()
                collection.upsert(ids=[c["id"] for c in items], documents=[c["text"] for c in items],
                                  metadatas=[c["metadata"] for c in items], embeddings=vectors)
            # User/model query is token-bounded too; never silently truncate an embedding input.
            query = model.tokenizer.decode(model.tokenizer.encode(query, add_special_tokens=False)[:200],
                                           skip_special_tokens=True)
            vector = model.encode([query], normalize_embeddings=True).tolist()
            result = collection.query(query_embeddings=vector, n_results=min(8, collection.count()),
                                      include=["documents", "metadatas", "distances"])
            return [{"chunk_id": i, "text": text, **meta, "distance": float(distance)}
                    for i, text, meta, distance in zip(result["ids"][0], result["documents"][0],
                                                       result["metadatas"][0], result["distances"][0])]
        except Handoff:
            raise
        except Exception:
            raise Handoff("retrieval", "Local source retrieval failed. No facts were guessed. Retry retrieval after checking local model/storage availability.") from None
        finally:
            if client is not None:
                # Chroma 1.x has no public close API. Release Windows file handles for retention.
                client._system.stop()
                from chromadb.api.client import SharedSystemClient
                SharedSystemClient.clear_system_cache()
                del client
                gc.collect()

    def tool(self):
        @tool
        def retrieve_sources(query: str) -> str:
            """Search this campaign's local event brief/calendar for source-backed facts, audience and tone."""
            if not query.strip() or len(query) > 1000:
                raise Handoff("retrieval", "Research tool query is empty or too long.")
            matches = self.search(query)
            # Full source audit prevents a top-k result from hiding a conflicting date or fee.
            return json.dumps({"matches": matches, "source_audit": self.store.get(self.cid, "docs")})
        return retrieve_sources
