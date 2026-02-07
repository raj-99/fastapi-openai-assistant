from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _mock_openai_ok(monkeypatch, answer_text="ok"):
    """
    Helper to mock OpenAI Responses API so tests never make network calls.

    It returns a minimal object that mimics openai==2.x response:
    response.output_text -> JSON string
    """
    class FakeResp:
        output_text = (
            f'{{"answer":"{answer_text}","sources":[],"confidence":0.5,"follow_ups":[]}}'
        )

    class FakeResponses:
        def create(self, **kwargs):
            return FakeResp()

    class FakeClient:
        responses = FakeResponses()

    def fake_get_openai_client():
        return FakeClient()

    # Patch the function *as imported in your route module*
    monkeypatch.setattr("app.routes.answer.get_openai_client", fake_get_openai_client)


def test_answer_returns_expected_shape(monkeypatch):
    _mock_openai_ok(monkeypatch)

    response = client.post("/api/answer", json={"question": "What is FastAPI?"})
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "sources" in data
    assert "confidence" in data
    assert "follow_ups" in data

    assert isinstance(data["sources"], list)
    assert isinstance(data["follow_ups"], list)
    assert 0.0 <= data["confidence"] <= 1.0


def test_answer_rejects_question_too_short():
    # This does NOT need OpenAI mocking because validation fails before OpenAI is called
    response = client.post("/api/answer", json={"question": "Hi"})
    assert response.status_code == 422  # validation error


def test_answer_returns_expected_answer(monkeypatch):
    _mock_openai_ok(monkeypatch, answer_text="ok")

    res = client.post("/api/answer", json={"question": "test"})
    assert res.status_code == 200
    assert res.json()["answer"] == "ok"


def test_answer_json_repair_success(monkeypatch):
    """
    Simulate model returning invalid JSON first, then valid JSON on repair.
    Ensures endpoint returns 200 and uses repaired JSON.
    """

    class FakeResp:
        def __init__(self, output_text: str):
            self.output_text = output_text

    class FakeResponses:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1

            # 1st call: invalid JSON (triggers JSONDecodeError)
            if self.calls == 1:
                return FakeResp('{"answer": "oops", "confidence": 0.5')  # missing braces, invalid JSON

            # 2nd call: valid JSON (repair output)
            return FakeResp('{"answer":"fixed","sources":[],"confidence":0.4,"follow_ups":[]}')

    class FakeClient:
        def __init__(self):
            self.responses = FakeResponses()

    # return the same FakeClient instance so the call counter increments
    fake_client = FakeClient()

    def fake_get_openai_client():
        return fake_client

    # Patch the get_openai_client that your route module uses
    monkeypatch.setattr("app.routes.answer.get_openai_client", fake_get_openai_client)

    res = client.post("/api/answer", json={"question": "test repair"})
    assert res.status_code == 200

    data = res.json()
    assert data["answer"] == "fixed"
    assert data["sources"] == []
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["follow_ups"] == []