"""
API Key Authentication Middleware.
SEC-1 fix: Protects destructive endpoints from unauthorized access.

Usage in route files:
    from middleware.auth import require_api_key

    @router.delete("/reset-all-data", dependencies=[Depends(require_api_key)])
    async def reset_all_data():
        ...
"""
import os
from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from config import logger

# ─── Configuration ───────────────────────────────────────────────────
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# API key loaded from environment — set API_SECRET_KEY in .env
_API_KEY = os.environ.get("API_SECRET_KEY")


async def require_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Dependency that enforces API key authentication.

    If API_SECRET_KEY is not set in environment, authentication is DISABLED
    (backward compatible with existing deployments).
    """
    if not _API_KEY:
        # Auth not configured — allow request (backward compat)
        logger.warning(
            "API_SECRET_KEY not set — authentication disabled. "
            "Set API_SECRET_KEY in .env for production security."
        )
        return None

    if not api_key or api_key != _API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide X-API-Key header."
        )
    return api_key


# ─── Endpoint Classification (for documentation) ────────────────────
# These sets define which endpoints SHOULD require auth when enabled.
# Route files reference require_api_key as a Depends() for protected routes.

PUBLIC_ENDPOINTS = {
    "/health",
    "/api/available-periods",
    "/api/available-data-periods",
}

READ_ENDPOINTS = {
    "/api/dashboard-summary",
    "/api/abc-analysis",
    "/api/capital-blocking-analysis",
    "/api/fastest-selling-items",
    "/api/group-analysis",
    "/api/inventory-analysis",
    "/api/database-view",
    "/api/upload-history",
    "/api/monthly-summaries",
    "/api/forecast-requirements",
    "/api/chatbot",
}

WRITE_ENDPOINTS = {
    "/api/upload-sales-data",
    "/api/financial-data",
    "/api/generate-daily-report",
    "/api/upload-forecast-history",
    "/api/generate-monthly-summary",
    "/api/generate-yearly-summary",
    "/api/trigger-summary-generation",
    "/api/extract-canteen-summary",
}

ADMIN_ENDPOINTS = {
    "/api/reset-all-data",
    "/api/clear-data",
    "/api/undo-upload/{upload_id}",
}
