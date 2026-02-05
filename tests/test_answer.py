import types
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_answers_return_expected_answer():
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

def test_answers_return_question_too_short():
    response = client.post("/api/answer", json={"question": "Hi"})
    assert response.status_code == 422  # Unprocessable Entity for validation error
    
def test_answer_with_mocked_openai(monkeypatch):
    # Fake OpenAI client + response structure
    class FakeResponses:
        def create(self, model, input):
            fake = types.SimpleNamespace()
            fake.output = [
                types.SimpleNamespace(
                    type="message",
                    content=[types.SimpleNamespace(type="output_text", text='{"answer":"ok","sources":[],"confidence":0.5,"follow_ups":[]}')]
                )
            ]
            return fake

    class FakeClient:
        responses = FakeResponses()

    def fake_get_client():
        return FakeClient()

    monkeypatch.setattr("app.routes.answer.get_client", fake_get_client)

    res = client.post("/api/answer", json={"question": "test"})
    assert res.status_code == 200
    data = res.json()
    assert data["answer"] == "ok"