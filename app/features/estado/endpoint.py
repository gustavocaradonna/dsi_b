"""Slice estado — GET /estado/{thread_id}: historial de la conversación guardado en la memoria."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.agente.servicio import obtener_agente
from app.shared import guardrails

router = APIRouter(tags=["estado"])


def _enmascarar(datos: dict) -> dict:
    """La memoria guarda los mensajes tal cual (el agente necesita el teléfono para reservar); lo que
    sale por HTTP pasa por el mismo enmascarado que las respuestas de /consultar."""
    for entrada in datos["historial"]:
        if "contenido" in entrada:
            entrada["contenido"] = guardrails.enmascarar_datos_personales(entrada["contenido"]).texto
        for herramienta in entrada.get("herramientas", []):
            if "telefono" in herramienta["argumentos"]:
                herramienta["argumentos"]["telefono"] = "[TELEFONO]"
    return datos


@router.get("/estado/{thread_id}")
def estado(thread_id: str, agente=Depends(obtener_agente)) -> dict:
    datos = agente.estado(thread_id)
    if datos is None:
        raise HTTPException(404, detail={"motivo": "thread_inexistente", "thread_id": thread_id})
    return _enmascarar(datos)
