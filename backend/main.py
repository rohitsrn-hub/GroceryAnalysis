"""
Application entrypoint — wires all modular components together.
Replaces the monolithic server.py initialization and route registration.

This file is the ONLY place where:
1. The FastAPI app is created
2. CORS middleware is configured
3. Route modules are registered
4. Database lifecycle is managed
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from config import (
    logger,
    CORS_ORIGINS_RAW,
    CORS_ALLOW_CREDENTIALS,
)
from database import db, client, ensure_indexes


# ─── Application Lifecycle ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle manager."""
    # Startup
    logger.info("Starting Grocery Analytics API...")
    await ensure_indexes()
    logger.info("Database indexes verified. API ready.")
    yield
    # Shutdown
    logger.info("Shutting down — closing MongoDB connection.")
    client.close()


# ─── Create FastAPI App ──────────────────────────────────────────────

app = FastAPI(
    title="Grocery Analytics API",
    description="Production-grade grocery sales analytics platform",
    version="2.0.0",
    lifespan=lifespan,
)


# ─── CORS Configuration ─────────────────────────────────────────────

if CORS_ORIGINS_RAW.strip() == "":
    allow_origins = []
elif CORS_ORIGINS_RAW.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]

allow_credentials = CORS_ALLOW_CREDENTIALS

# Safety: wildcard + credentials is rejected by browsers
if allow_origins == ["*"] and allow_credentials:
    logger.warning(
        "CORS: wildcard origin with credentials not allowed; disabling credentials."
    )
    allow_credentials = False

logger.info(
    "CORS Configuration — origins=%s credentials=%s",
    allow_origins, allow_credentials,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check (no prefix) ───────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "grocery-analytics"}


# ─── Register Route Modules ─────────────────────────────────────────
# Each route module has its own APIRouter with prefix="/api"

from routes.admin import router as admin_router
from routes.analytics import router as analytics_router
from routes.financial import router as financial_router
from routes.summaries import router as summaries_router
from routes.chatbot import router as chatbot_router

app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(financial_router)
app.include_router(summaries_router)
app.include_router(chatbot_router)

# NOTE: The legacy server.py still serves the following routes that haven't
# been migrated yet: upload-sales-data, comprehensive-report, forecast-demand,
# dashboard-summary, daily-sales-trend, database-view, chatbot POST, etc.
# Those will be migrated in Phase 4. For now, the server.py `api_router`
# can be included alongside the modular routes for backward compatibility:
#
# from server import api_router as legacy_router
# app.include_router(legacy_router)

logger.info(
    "Registered %d route modules: admin, analytics, financial, summaries, chatbot",
    5,
)
