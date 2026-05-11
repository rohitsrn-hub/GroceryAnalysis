"""
Chatbot-related Pydantic models.
Extracted from server.py L5944-5950.
"""
from typing import Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
