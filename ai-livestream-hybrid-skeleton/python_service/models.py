from typing import Optional, Literal
from pydantic import BaseModel, Field

Emotion = Literal["neutral", "happy", "excited", "sad", "angry"]
Action = Literal["answer", "sell", "ignore", "fallback"]

class SpeakRequest(BaseModel):
    reply: str = Field(..., min_length=1, max_length=500)
    emotion: Emotion = "neutral"
    action: Action = "answer"
    source_user: Optional[str] = None
    comment: Optional[str] = None
    request_id: Optional[str] = None

class SpeakResponse(BaseModel):
    status: str
    request_id: str
    tts_provider: str
    avatar_provider: str
    message: str
