import json
import logging
from fastapi import APIRouter, HTTPException, Request
from app.schemas import AskRequest, AnswerResponse
from app.rag.embeddings import embed_texts
from app.rag.retrieval import retrieve_top_k
from app.core.openai_client import get_openai_client
from app.core.config import settings

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

@router.post("/ask", response_model=AnswerResponse)
def ask(askRequest: AskRequest, request: Request) -> AnswerResponse:
    request_id = getattr(request.state, "request_id", "no-request-id")
    logger.info(f"request_id={request_id} | /api/ask | q={askRequest.question!r}")
    
    query_vector = embed_texts([askRequest.question])[0]
    
    hits = retrieve_top_k(query_vector, top_k=askRequest.top_k)
    relevant_hits = [hit for hit in hits if hit["score"] >= askRequest.min_score]
    retrieved_ids = [hit["id"] for hit in hits]
    
    if not relevant_hits:
        return AnswerResponse(
            answer="I don't know based on the current knowledge base.",
            sources=[],
            confidence=0.2,
            follow_ups=["Try ingesting more relevant documents."],
        )
    
    context = "\n\n".join([f"[Source hit {hit['id']} | score={hit['score']:.2f}]\n{hit['content']}" for hit in relevant_hits])
    user_text = f"Question: {askRequest.question}\n\nContext:\n{context}"
    
    client = get_openai_client()
    response = client.responses.create(
        model=settings.openai_model,
        instructions=RAG_PROMPT,
        input=user_text,
    )
    raw = (response.output_text or "").strip()
    clean = _strip_code_fences(raw)
    
    
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        logger.error(f"request_id={request_id} | Model returned invalid JSON | raw_response={raw!r}")
        raise HTTPException(status_code=502, detail="Model returned invalid JSON")

    data["sources"] = retrieved_ids
    
    return AnswerResponse(**data)