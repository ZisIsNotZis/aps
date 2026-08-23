"""APS Backend — unified planning API.

This module provides the FastAPI application with CORS, a health check,
and the unified planning router mounted at /api/unified.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aps.unified.api import router as _unified_router

logger = logging.getLogger(__name__)

app = FastAPI(title="APS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


app.include_router(_unified_router)
