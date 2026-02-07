import logging
import json
import time
import random
from fastapi import APIRouter, HTTPException, Request
from openai import APIConnectionError, AuthenticationError, RateLimitError
from app.schemas import AnswerRequest, AnswerResponse
from app.core.openai_client import get_openai_client
from app.core.config import settings

logger = logging.getLogger("answer")
router = APIRouter()

JSON_REPAIR_INSTRUCTIONS = """You will be given text that should represent JSON for this schema:

AnswerResponse = {
  "answer": string,
  "sources": string[],
  "confidence": number (0..1),
  "follow_ups": string[]
}

Return ONLY valid JSON for AnswerResponse. No markdown. No extra text. No explanation.
If fields are missing, infer reasonable defaults:
sources=[], follow_ups=[], confidence=0.3
"""

SYSTEM_PROMPT = """You are a helpful AI assistant.
Return JSON ONLY that matches the schema: AnswerResponse with keys:
answer (string), sources (array of strings), confidence (0..1), follow_ups (array of strings).
If you are unsure, keep confidence low and ask follow-up questions.
"""

def _call_openai_with_retries(client, *, model: str, instructions: str, user_text:str, request_id: str):
    max_retries = 3 # total attempts = initial try + 2 retries
    base_delay = 0.6 # seconds
    max_delay = 8.0 # seconds
    
    last_exc = None
    
    for attempt in range(max_retries):
        try:
            return client.responses.create(
                model=model,
                instructions=instructions,
                input=user_text,
            )
        except(RateLimitError, APIConnectionError) as e:
            last_exc = e
            
            # If this was the last attempt, raise and let handlers respond
            if attempt == max_retries - 1:
                raise
            
            # Exponential backoff with jitter
            delay = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 0.25)
            
            logger.warning(
                f"request_id={request_id} | transient error={type(e).__name__} | "
                f"attempt={attempt + 1}/{max_retries} | sleeping={delay:.2f}s"
            )
            time.sleep(delay)
        
    raise last_exc # Should never reach here

def _parse_and_validate_answer(raw: str) -> AnswerResponse:
    data = json.loads(raw)
    return AnswerResponse(**data)

@router.post("/answer", response_model=AnswerResponse)
def answer(answer_request: AnswerRequest, request: Request) -> AnswerResponse:
    start = time.time()
    request_id = getattr(request.state, "request_id", "no-request-id")
    logger.info(f"request_id={request_id} | received question={answer_request.question!r}")
    
    try:
        # Placeholder for actual answer generation logic
        client = get_openai_client()
        
        #Build user message with optional context.
        user_text = f"Question: {answer_request.question}"
        if answer_request.context:
            user_text += f"\n\nContext:\n{answer_request.context}"
            
        response = _call_openai_with_retries(
            client,
            model=settings.openai_model,
            instructions=SYSTEM_PROMPT,
            user_text=user_text,
            request_id=request_id,
        )
        
        # SDK helper: returns the combined text output
        raw = (response.output_text or "").strip()
        
        # Parse JSON -> AnswerResponse
        # Treat model output as untrusted until validated.
        data = json.loads(raw)
        validated = AnswerResponse(**data)
        
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(f"request_id={request_id} | SUCCESS | elapsed_ms={elapsed_ms}")
        return validated
    
    except json.JSONDecodeError:
        logger.warning(f"request_id={request_id} | model returned invalid JSON, attempting repair")
        
        try:
            repair_response = _call_openai_with_retries(
                client,
                model=settings.openai_model,
                instructions=JSON_REPAIR_INSTRUCTIONS,
                user_text=raw,
                request_id=request_id,
            )
            fixed = (repair_response.output_text or "").strip()
            validated = _parse_and_validate_answer(fixed)
            
            elapsed_ms = int((time.time() - start) * 1000)
            logger.info(f"request_id={request_id} | SUCCESS_AFTER_REPAIR | elapsed_ms={elapsed_ms}")
            return validated
        except Exception:
            logger.warning(f"request_id={request_id} | JSON repair failed!")
            raise HTTPException(status_code=502, detail="Model returned invalid JSON and repair failed")
    
    except AuthenticationError:
        logger.error(f"request_id={request_id} | invalid OpenAI API key")
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key")

    except RateLimitError:
        logger.warning(f"request_id={request_id} | rate limited")
        raise HTTPException(status_code=429, detail="Rate limited by OpenAI")

    except APIConnectionError:
        logger.warning(f"request_id={request_id} | OpenAI connection error")
        raise HTTPException(status_code=502, detail="OpenAI connection error")

    except RuntimeError as e:
        logger.error(f"request_id={request_id} | CONFIG ERROR : {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        logger.exception(f"request_id={request_id} | ERROR | failed to generate answer: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")        
        
    # CoPilot Generated below sample code - may be useful for implementation reference
    # # Simulate processing the question and generating an answer
    # if len(req.question) < 3:
    #     logger.error("Question is too short")
    #     raise HTTPException(status_code=400, detail="Question must be at least 3 characters long")
    
    # # Dummy answer generation logic
    # answer_text = f"This is a dummy answer to your question: '{req.question}'"
    # sources = [f"source_{uuid.uuid4()}.txt"]
    # confidence = 0.85
    # follow_ups = ["Can you provide more details?", "What is the context?"]
    
    # logger.info("Answer generated successfully")
    
    # return AnswerResponse(
    #     answer=answer_text,
    #     sources=sources,
    #     confidence=confidence,
    #     follow_ups=follow_ups
    # )