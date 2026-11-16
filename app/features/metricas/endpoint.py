"""Slice metricas — GET /metricas: consultas, errores, bloqueos, latencia promedio y p95, herramientas,
tokens y costo estimado del proceso actual."""

from __future__ import annotations

from fastapi import APIRouter

from app.shared.observabilidad import metricas

router = APIRouter(tags=["observabilidad"])


@router.get("/metricas")
def obtener_metricas() -> dict:
    return metricas.resumen()
