"""Slice health — GET /health."""

from __future__ import annotations

from fastapi import APIRouter

from app.shared import config

router = APIRouter(tags=["observabilidad"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "memoria": config.RUTA_MEMORIA.name, "max_iteraciones": config.MAX_ITERACIONES}
