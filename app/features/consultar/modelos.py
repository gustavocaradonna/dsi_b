"""Contrato HTTP del slice consultar."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Consulta(BaseModel):
    mensaje: str = Field(..., description="Mensaje del cliente, texto libre", examples=["¿Tienen hidrolavadora para el sábado?"])
    thread_id: str | None = Field(
        None,
        description="Id de la conversación. Si no se manda, se crea uno nuevo y se devuelve en la respuesta.",
        max_length=100,
        pattern=r"^[\w\-]+$",
    )


class Respuesta(BaseModel):
    thread_id: str
    respuesta: str
    herramientas_usadas: list[str]
    iteraciones: int
    corte_por_limite: bool
    datos_enmascarados: dict[str, int]
    latencia_ms: float
    tokens: dict[str, int]
    costo_estimado_usd: float
