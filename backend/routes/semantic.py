"""
Semantic routes — generation and management of semantic embeddings.
"""
from fastapi import APIRouter, HTTPException

from config import logger
from services.semantic_service import generate_all_embeddings

router = APIRouter(prefix="/api", tags=["semantic"])

@router.post("/embeddings/generate")
async def generate_embeddings():
    """Trigger the generation of semantic embeddings for all unique items."""
    try:
        result = await generate_all_embeddings()
        return result
    except Exception as e:
        logger.exception(f"Error generating embeddings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embeddings: {str(e)}"
        )

@router.get("/embeddings/status")
async def get_embeddings_status():
    """Get the status/size of the in-memory embeddings cache."""
    from services.semantic_service import _EMBEDDINGS_CACHE
    return {
        "cache_loaded": len(_EMBEDDINGS_CACHE) > 0,
        "cache_size": len(_EMBEDDINGS_CACHE)
    }

