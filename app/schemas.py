from pydantic import BaseModel, Field
from typing import Optional,List

class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=3, description="User's question to be answered")
    context: Optional[str] = Field(None, description="Optional context/policy text to be used for answering the question")

class AnswerResponse(BaseModel):
    answer: str
    sources: List[str] = []
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    follow_ups: List[str] = []