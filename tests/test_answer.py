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