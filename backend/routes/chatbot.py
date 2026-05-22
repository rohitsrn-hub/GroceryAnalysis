"""
Chatbot routes — AI-powered sales analytics chatbot.
Extracted from server.py L5940-6705.

Routes:
- POST /chatbot
- GET /chat-history/{session_id}
- DELETE /chat-history/{session_id}
"""
from fastapi import APIRouter, HTTPException, Query

from config import logger
from database import db
from models.chat import ChatMessage, ChatResponse

router = APIRouter(prefix="/api", tags=["chatbot"])


@router.get("/chat-history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100)
):
    """Get chat history for a specific session."""
    try:
        history = await db.chat_history.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", 1).limit(limit).to_list(limit)

        return {"session_id": session_id, "messages": history}
    except Exception as e:
        logger.exception(f"Error fetching chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching chat history: {str(e)}"
        )


@router.delete("/chat-history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a specific session."""
    try:
        result = await db.chat_history.delete_many({"session_id": session_id})
        return {
            "deleted_count": result.deleted_count,
            "session_id": session_id
        }
    except Exception as e:
        logger.exception(f"Error clearing chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing chat history: {str(e)}"
        )


@router.post("/chatbot", response_model=ChatResponse)
async def chat_with_data(request: ChatMessage):
    """AI Chatbot — answers questions about sales data using GPT-4o."""
    try:
        from services.chatbot_service import handle_chat

        result = await handle_chat(
            message=request.message,
            session_id=request.session_id,
        )
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        logger.exception(f"Chatbot error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")
