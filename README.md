# FastAPI OpenAI Assistant
Production-style FastAPI skeleton

## Current Features
- `GET /api/health` health check
- `POST /api/answer` mocked response (will become OpenAI-powered)
- Strict request/response validation with Pydantic
- Centralized logging
- Request ID middleware (trace every request)
- Test suite with pytest
- `.env` support via `.env.example`
- `requirements.txt` + `requirements-dev.txt`

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

## API Endpoints

GET /api/health
Response:
{ "status": "ok" }

POST /api/answer (mocked for now)
Request:
{
  "question": "What is RAG?",
  "context": "Optional context/policy text"
}

Response shape:
{
  "answer": "(mock) You asked: What is RAG?",
  "sources": ["provided_context"],
  "confidence": 0.55,
  "follow_ups": ["...", "..."]
}

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

## Request Tracing (x-request-id)

Every request gets a x-request-id header:
- If the client sends one, the server uses it
- Otherwise, the server generates a UUID
- The same ID is returned in the response headers

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

## Setup (Windows PowerShell)

1) Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

2) Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

3) Configure environment variables
Copy .env.example to .env
Copy-Item .env.example .env

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

## Run Locally

uvicorn app.main:app --reload

Open:
- Swagger docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

## Example Requests

Health check
curl http://127.0.0.1:8000/api/health

Answer endpoint
curl -X POST http://127.0.0.1:8000/api/answer `
  -H "Content-Type: application/json" `
  -d "{""question"":""What is RAG?"",""context"":""RAG = retrieval augmented generation.""}"

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

## Run Tests (recommended on Windows)

python -m pytest -q

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-