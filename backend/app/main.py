"""
CLAIM LAGOS - FastAPI Application Entry Point
Electoral Intelligence Platform for APC Lagos State Campaign Council
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import structlog

from app.core.config import settings
from app.api.router import api_router
from app.core.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.api.ws import router as ws_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("claim_lagos_starting", env=settings.APP_ENV)
    # Future: warm embedding model, connect pools, etc.
    yield
    logger.info("claim_lagos_shutdown")


app = FastAPI(
    title="CLAIM LAGOS API",
    description="Digital Intelligence & Grassroots Mobilisation Platform - APC Lagos State Campaign Council",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, auth_per_minute=20)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "CLAIM LAGOS",
        "version": "0.1.0",
        "env": settings.APP_ENV,
    }


@app.get("/")
async def root():
    return {
        "message": "CLAIM LAGOS API",
        "docs": "/api/docs",
        "health": "/health",
    }
