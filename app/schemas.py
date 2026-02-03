from pydantic import BaseModel, Field

class AnswerRequest(BaseModel):
    """
    Input contract for /answer.
    - Validates user input automatically (rejects bad requests with 422).
    - Creates a stable interface your frontend or other services can rely on.
    """
    question: str = Field(..., min_length=3, description="User's question to be answered")
    context: str | None = Field(None, description="Optional context/policy text to be used for answering the question")

class AnswerResponse(BaseModel):
    """
    Output contract for /answer.
    """
    answer: str
    sources: list[str] = []
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    follow_ups: list[str] = []