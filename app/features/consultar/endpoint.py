"""Slice consultar — POST /consultar."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.agente.servicio import obtener_agente
from app.features.consultar import handler
from app.features.consultar.modelos import Consulta, Respuesta

router = APIRouter(tags=["consultar"])


@router.post("/consultar", response_model=Respuesta)
def consultar(consulta: Consulta, agente=Depends(obtener_agente)) -> Respuesta:
    """Mensaje del cliente -> guardrails de entrada -> agente -> enmascarado de salida."""
    try:
        return handler.ejecutar(consulta, agente)
    except handler.ConsultaBloqueada as b:
        raise HTTPException(400, detail={"motivo": b.motivo, "mensaje": b.mensaje, "thread_id": b.thread_id}) from None
    except handler.ErrorDelAgente as e:
        raise HTTPException(500, detail={"motivo": "error_interno", "thread_id": e.thread_id}) from None
