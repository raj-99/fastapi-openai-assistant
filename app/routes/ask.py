import json
import logging
from fastapi import APIRouter, HTTPException, Request
from app.schemas import AskRequest, AnswerResponse
from app.rag.embeddings import embed_texts
from app.rag.retrieval import retrieve_top_k
from app.core.openai_client import get_openai_client
from app.core.config import settings
import time
import random
from openai import APIConnectionError, RateLimitError

# ToDo: Add the same retries + JSON repair to /api/ask

logger = logging.getLogger("ask")
router = APIRouter()

RAG_PROMPT = """You are a helpful assistant.
You MUST answer using ONLY the provided context.
If the context is insufficient, say you don't know.

Return JSON ONLY matching AnswerResponse:
answer (string), sources (array of strings), confidence (0..1), follow_ups (array of strings).
Do not wrap the JSON in markdown or code fences.
"""
def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # Remove starting ``` or ```json
        s = s.split("\n", 1)[1] if "\n" in s else ""
        # Remove trailing ```
        if s.rstrip().endswith("```"):
            s = s.rsplit("```", 1)[0]
    return s.strip()

JSON_REPAIR_INSTRUCTIONS = """You will be given text that should represent JSON for this schema:

AnswerResponse = {
  "answer": string,
  "sources": string[],
  "confidence": number (0..1),
  "follow_ups": string[]
}

Return ONLY valid JSON for AnswerResponse. No markdown. No code fences. No extra text.
If fields are missing, infer defaults: sources=[], follow_ups=[], confidence=0.3
"""

def _call_openai_with_retries(client, *, model: str, instructions: str, user_text: str, request_id: str):
    max_retries = 3  # 1 initial + 2 retries
    base_delay = 0.6
    max_delay = 8.0
    last_exc = None

    for attempt in range(max_retries):
        try:
            return client.responses.create(
                model=model,
                instructions=instructions,
                input=user_text,
            )
        except (RateLimitError, APIConnectionError) as e:
            last_exc = e
            if attempt == max_retries - 1:
                raise

            delay = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 0.25)
            logger.warning(
                f"request_id={request_id} | transient error={type(e).__name__} | "
                f"attempt={attempt + 1}/{max_retries} | sleeping={delay:.2f}s"
            )
            time.sleep(delay)

    raise last_exc

def _parse_answer_json(text: str) -> dict:
    clean = _strip_code_fences((text or "").strip())
    return json.loads(clean)

@router.post("/ask", response_model=AnswerResponse)
def ask(ask_request: AskRequest, request: Request) -> AnswerResponse:
    request_id = getattr(request.state, "request_id", "no-request-id")
    logger.info(f"request_id={request_id} | /api/ask | q={ask_request.question!r}")
    
    query_vector = embed_texts([ask_request.question])[0]
    
    hits = retrieve_top_k(query_vector, top_k=ask_request.top_k)
    relevant_hits = [hit for hit in hits if hit["score"] >= ask_request.min_score]
    retrieved_ids = [hit["id"] for hit in relevant_hits]
    
    if not relevant_hits:
        return AnswerResponse(
            answer="I don't know based on the current knowledge base.",
            sources=[],
            confidence=0.2,
            follow_ups=["Try ingesting more relevant documents."],
        )
    
    context = "\n\n".join([f"[Source hit {hit['id']} | score={hit['score']:.2f}]\n{hit['content']}" for hit in relevant_hits])
    user_text = f"Question: {ask_request.question}\n\nContext:\n{context}"
    
    client = get_openai_client()
    
    response = _call_openai_with_retries(
        client,
        model=settings.openai_model,
        instructions=RAG_PROMPT,
        user_text=user_text,
        request_id=request_id,
    )
    raw = (response.output_text or "").strip()
    # clean = _strip_code_fences(raw)
    
    
    try:
        data = _parse_answer_json(raw)
    except json.JSONDecodeError:
        logger.warning(f"request_id={request_id} | invalid JSON, attempting repair")
        repair_resp = _call_openai_with_retries(
            client,
            model=settings.openai_model,
            instructions=JSON_REPAIR_INSTRUCTIONS,
            user_text=raw,
            request_id=request_id,
        )
        fixed_raw = (repair_resp.output_text or "").strip()
        try:
            data = _parse_answer_json(fixed_raw)
        except Exception as e:
            logger.error(f"request_id={request_id} | JSON repair failed | raw_response={raw!r}")
            raise HTTPException(status_code=502, detail="Model returned invalid JSON")

    data["sources"] = retrieved_ids
    
    return AnswerResponse(**data)