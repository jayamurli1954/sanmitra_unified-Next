import asyncio
from datetime import datetime, timezone

import app.modules.rag.service as rag_service
from app.modules.rag.schemas import RagLegalFilter, RagQueryRequest
from app.modules.rag.service import _build_filter, _chunk_text, _hybrid_score, _tokenize


def test_chunk_text_splits_long_content() -> None:
    text = " ".join(["legal" for _ in range(1500)])
    chunks = _chunk_text(text, chunk_size=500, chunk_overlap=60)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)
    assert all(c.strip() for c in chunks)


def test_hybrid_score_prefers_related_chunk() -> None:
    query = "how to file a trust deed amendment"
    query_tokens = set(_tokenize(query))
    # Simple synthetic embedding space for deterministic unit test
    query_embedding = [1.0, 0.0, 0.0]

    related_text = "To file a trust deed amendment, submit the amendment petition before the registrar with supporting trust records."
    unrelated_text = "Temple donation receipts and sevas are listed in the financial dashboard for monthly accounting."

    related_chunk = {
        "text": related_text,
        "token_set": sorted(set(_tokenize(related_text))),
        "embedding": [1.0, 0.0, 0.0],
    }
    unrelated_chunk = {
        "text": unrelated_text,
        "token_set": sorted(set(_tokenize(unrelated_text))),
        "embedding": [0.0, 1.0, 0.0],
    }

    related_score = _hybrid_score(query_embedding, query_tokens, related_chunk)
    unrelated_score = _hybrid_score(query_embedding, query_tokens, unrelated_chunk)

    assert related_score > unrelated_score


def test_build_filter_enforces_tenant_and_app() -> None:
    payload = RagQueryRequest(
        query="trust registration",
        source_types=["judgment", "statute"],
        tags=["civil", "trust"],
        language="en",
    )

    filters = _build_filter(tenant_id="tenant-1", app_key="legalmitra", payload=payload)

    assert filters["tenant_id"] == "tenant-1"
    assert filters["app_key"] == "legalmitra"
    assert filters["language"] == "en"
    assert filters["source_type"] == {"$in": ["judgment", "statute"]}
    assert filters["tags"] == {"$in": ["civil", "trust"]}


def test_build_filter_includes_legal_filters() -> None:
    payload = RagQueryRequest(
        query="section 138 cheque bounce",
        legal_filters=RagLegalFilter(
            jurisdiction="karnataka",
            court_name="high court",
            act_name="negotiable instruments act",
            section="138",
            matter_type="criminal",
            citation_contains="SCC",
        ),
    )

    filters = _build_filter(tenant_id="tenant-1", app_key="legalmitra", payload=payload)

    assert filters["legal_jurisdiction"] == "karnataka"
    assert filters["legal_court_name"] == "high court"
    assert filters["legal_act_name"] == "negotiable instruments act"
    assert filters["legal_section"] == "138"
    assert filters["legal_matter_type"] == "criminal"
    assert filters["legal_citation"] == {"$regex": "scc", "$options": "i"}


class _FakeCursor:
    def __init__(self, chunks):
        self._chunks = chunks

    def sort(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def __aiter__(self):
        self._iter = iter(self._chunks)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeChunksCollection:
    def __init__(self, chunks):
        self.chunks = chunks
        self.filters = []

    def find(self, filters):
        self.filters.append(filters)
        return _FakeCursor(self.chunks)


class _FakeEmbeddingProvider:
    name = "fake"
    model_name = "fake-v1"

    async def embed_texts(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def _chunk(
    text: str,
    *,
    act_name: str = "Bharatiya Nagarik Suraksha Sanhita, 2023",
    tenant_id: str = "tenant-1",
    app_key: str = "legalmitra",
    document_id: str = "doc-1",
):
    return {
        "document_id": document_id,
        "chunk_id": f"chunk-{document_id}",
        "tenant_id": tenant_id,
        "app_key": app_key,
        "chunk_index": 0,
        "title": "BNSS procedure note",
        "source_type": "statute",
        "source_uri": "https://example.test/bnss",
        "language": "en",
        "tags": ["statute"],
        "legal_metadata": {"act_name": act_name},
        "text": text,
        "token_set": sorted(set(_tokenize(text))),
        "embedding": [1.0, 0.0, 0.0],
    }


def test_query_knowledge_auto_scopes_detected_act(monkeypatch) -> None:
    text = "Section 173 BNSS explains FIR registration procedure under Bharatiya Nagarik Suraksha Sanhita."
    collection = _FakeChunksCollection([_chunk(text)])

    monkeypatch.setattr(rag_service, "get_collection", lambda _name: collection)
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: _FakeEmbeddingProvider())
    monkeypatch.setattr(rag_service, "get_embedding_strategy_name", lambda: "fake_hash")
    monkeypatch.setattr(rag_service, "should_trigger_jit", lambda _query: False)

    result = asyncio.run(
        rag_service.query_knowledge(
            tenant_id="tenant-1",
            app_key="legalmitra",
            payload=RagQueryRequest(query="Explain section 173 BNSS FIR procedure"),
        )
    )

    assert result["strategy"] == "fake_hash_act_scoped_bnss"
    assert collection.filters[0]["tenant_id"] == "tenant-1"
    assert collection.filters[0]["app_key"] == "legalmitra"
    assert collection.filters[0]["legal_act_name"]["$options"] == "i"
    assert "Bharatiya\\ Nagarik\\ Suraksha\\ Sanhita" in collection.filters[0]["legal_act_name"]["$regex"]


def test_query_knowledge_does_not_override_explicit_act_filter(monkeypatch) -> None:
    text = "Custom Act section 1 filing procedure and documentary requirements for a specific legal workflow."
    collection = _FakeChunksCollection([_chunk(text, act_name="custom act")])

    monkeypatch.setattr(rag_service, "get_collection", lambda _name: collection)
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: _FakeEmbeddingProvider())
    monkeypatch.setattr(rag_service, "get_embedding_strategy_name", lambda: "fake_hash")
    monkeypatch.setattr(rag_service, "should_trigger_jit", lambda _query: False)

    result = asyncio.run(
        rag_service.query_knowledge(
            tenant_id="tenant-1",
            app_key="legalmitra",
            payload=RagQueryRequest(
                query="Custom Act section 1 filing procedure BNSS",
                legal_filters=RagLegalFilter(act_name="Custom Act"),
            ),
        )
    )

    assert result["strategy"] == "fake_hash"
    assert collection.filters[0]["legal_act_name"] == "custom act"


def test_query_knowledge_never_returns_cross_tenant_or_cross_app_citations(monkeypatch) -> None:
    owned_text = "Section 173 BNSS explains FIR registration procedure and documentary requirements."
    collection = _FakeChunksCollection(
        [
            _chunk(
                "FOREIGN_TENANT_SECRET Section 173 BNSS FIR registration procedure.",
                tenant_id="tenant-b",
                document_id="foreign-tenant",
            ),
            _chunk(
                "FOREIGN_APP_SECRET Section 173 BNSS FIR registration procedure.",
                app_key="mandirmitra",
                document_id="foreign-app",
            ),
            _chunk(owned_text, document_id="owned"),
        ]
    )

    monkeypatch.setattr(rag_service, "get_collection", lambda _name: collection)
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: _FakeEmbeddingProvider())
    monkeypatch.setattr(rag_service, "get_embedding_strategy_name", lambda: "fake_hash")
    monkeypatch.setattr(rag_service, "should_trigger_jit", lambda _query: False)

    result = asyncio.run(
        rag_service.query_knowledge(
            tenant_id="tenant-1",
            app_key="legalmitra",
            payload=RagQueryRequest(
                query="Explain section 173 BNSS FIR procedure",
                include_context=True,
            ),
        )
    )

    assert collection.filters[0]["tenant_id"] == "tenant-1"
    assert collection.filters[0]["app_key"] == "legalmitra"
    assert [citation["document_id"] for citation in result["citations"]] == ["owned"]
    rendered = f"{result['answer']}\n{result['context']}"
    assert "FOREIGN_TENANT_SECRET" not in rendered
    assert "FOREIGN_APP_SECRET" not in rendered


def test_list_documents_never_serializes_cross_tenant_or_cross_app_records(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    owned = {
        **_chunk("Owned legal document content with sufficient detail for indexing."),
        "created_at": now,
        "embedding_provider": "fake",
        "embedding_model": "fake-v1",
        "chunk_count": 1,
    }
    foreign_tenant = {**owned, "document_id": "foreign-tenant", "tenant_id": "tenant-b"}
    foreign_app = {**owned, "document_id": "foreign-app", "app_key": "mandirmitra"}
    collection = _FakeChunksCollection([foreign_tenant, foreign_app, owned])
    monkeypatch.setattr(rag_service, "get_collection", lambda _name: collection)

    items = asyncio.run(
        rag_service.list_documents(tenant_id="tenant-1", app_key="legalmitra", limit=50)
    )

    assert collection.filters == [{"tenant_id": "tenant-1", "app_key": "legalmitra"}]
    assert [item["document_id"] for item in items] == ["doc-1"]

