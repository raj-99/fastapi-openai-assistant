import logging
from fastapi import APIRouter, HTTPException, Request
from app.schemas import AnswerRequest, AnswerResponse
from app.core.openai_client import get_client
from app.core.config import settings

logger = logging.getLogger("answer")
router = APIRouter()

SYSTEM_PROMPT = """You are a helpful AI assistant.
Return JSON ONLY that matches the schema: AnswerResponse with keys:
answer (string), sources (array of strings), confidence (0..1), follow_ups (array of strings).
If you are unsure, keep confidence low and ask follow-up questions.
"""

@router.post("/answer", response_model=AnswerResponse)
def answer(answer_request: AnswerRequest, request: Request) -> AnswerResponse:
    request_id = getattr(request.state, "request_id", "no-request-id")
    logger.info(f"request_id={request_id} | received question={answer_request.question!r}")
    
    try:
        # Placeholder for actual answer generation logic
        client = get_client()
        
        #Build user message with optional context.
        user_text = f"Question: {answer_request.question}"
        if answer_request.context:
            user_text += f"\n\nContext:\n{answer_request.context}"
            
        response = client.responses.create(
            model=settings.openai_model,
            input = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
        )
        
        # The Responses API may return text in various output formats.
        # We'll extract combined text and parse as JSON.
        
        text = ""
        for item in response.output:
            if item.type == "message":
                for chunk in item.content:
                    if chunk.type == "output_text":
                        text += chunk.text
        
         # Parse JSON -> AnswerResponse
        # Treat model output as untrusted until validated.
        import json
        data = json.loads(text)
        validated = AnswerResponse(**data)
        
        logger.info(f"request_id={request_id} | SUCCESS")
        return validated

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