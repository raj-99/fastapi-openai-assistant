import types
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ask_parses_code_fenced_json_and_enforces_sources(monkeypatch):
    """
    - OpenAI returns JSON wrapped in ```json fences
    - Model sources are wrong / missing :0 suffix
    - We enforce sources from retriever (relevant_hits)
    """

    # 1) Mock embeddings so we don't call OpenAI embeddings
    def fake_embed_texts(texts):
        # Return a deterministic vector (length doesn't matter for mocked retrieval)
        return [[0.0, 0.1, 0.2]]

    monkeypatch.setattr("app.routes.ask.embed_texts", fake_embed_texts)

    # 2) Mock retrieval to return deterministic relevant hits
    fake_hits = [
        {"id": "fastapi_notes:0", "source": "fastapi_notes", "chunk_index": 0, "content": "FastAPI is a modern Python web framework...", "score": 0.95},
        {"id": "pgvector_notes:1", "source": "pgvector_notes", "chunk_index": 1, "content": "pgvector enables vector search...", "score": 0.30},
    ]

    def fake_retrieve_top_k(query_vector, top_k):
        return fake_hits

    monkeypatch.setattr("app.routes.ask.retrieve_top_k", fake_retrieve_top_k)

    # 3) Mock OpenAI client so responses.create returns code-fenced JSON
    class FakeResp:
        output_text = """```json
{
  "answer": "FastAPI is a modern Python web framework.",
  "sources": ["WRONG_SOURCE_ID"],
  "confidence": 1.0,
  "follow_ups": ["Do you want an example?"]
}
```"""

    class FakeResponses:
        def create(self, **kwargs):
            return FakeResp()

    class FakeClient:
        responses = FakeResponses()

    def fake_get_openai_client():
        return FakeClient()

    monkeypatch.setattr("app.routes.ask.get_openai_client", fake_get_openai_client)

    # 4) Call API
    res = client.post("/api/ask", json={"question": "What is FastAPI?", "top_k": 5, "min_score": 0.2})
    assert res.status_code == 200

    data = res.json()
    assert data["answer"]  # non-empty
    # Enforced from relevant_hits (score >= 0.2)
    assert data["sources"] == ["fastapi_notes:0", "pgvector_notes:1"]
    assert 0.0 <= data["confidence"] <= 1.0
    assert isinstance(data["follow_ups"], list)


def test_ask_repairs_invalid_json(monkeypatch):
    """
    First OpenAI call returns invalid JSON -> triggers repair flow.
    Repair call returns valid JSON (optionally fenced) -> endpoint returns 200.
    """

    # Mock embeddings
    monkeypatch.setattr("app.routes.ask.embed_texts", lambda texts: [[0.0, 0.1, 0.2]])

    # Mock retrieval
    monkeypatch.setattr(
        "app.routes.ask.retrieve_top_k",
        lambda query_vector, top_k: [{"id": "fastapi_notes:0", "source": "fastapi_notes", "chunk_index": 0, "content": "FastAPI...", "score": 0.9}],
    )

    # Fake OpenAI with a call counter: invalid first, valid second
    class FakeResponses:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                # invalid JSON (missing closing brace)
                return types.SimpleNamespace(output_text='{"answer":"x","sources":[],"confidence":0.5,"follow_ups":[]')
            # valid JSON (can be fenced too)
            return types.SimpleNamespace(output_text='{"answer":"fixed","sources":[],"confidence":0.4,"follow_ups":[]}')

    fake_responses = FakeResponses()

    class FakeClient:
        responses = fake_responses

    monkeypatch.setattr("app.routes.ask.get_openai_client", lambda: FakeClient())

    res = client.post("/api/ask", json={"question": "What is FastAPI?", "top_k": 5, "min_score": 0.2})
    assert res.status_code == 200
    data = res.json()
    assert data["answer"] == "fixed"
    # sources enforced from retriever
    assert data["sources"] == ["fastapi_notes:0"]