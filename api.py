"""
api.py - API REST del agente (TP Final, Partes B, C y D).

    GET  /health               estado del servicio (y de las bases que necesita)
    POST /consultar            mensaje del cliente -> guardrails de entrada -> agente -> guardrail de salida
    GET  /estado/{thread_id}   historial de la conversacion guardado en la memoria SQLite
    GET  /metricas             consultas, errores, bloqueos, latencia promedio y p95, herramientas, tokens y costo

Levantar (desde la raiz del repo):
    uvicorn api:app --port 8000
Documentacion interactiva: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

import guardrails
from observabilidad import Metricas, costo_usd, log_evento

metricas = Metricas()


@lru_cache(maxsize=1)
def obtener_agente():
    """Un solo agente por proceso (el grafo compilado y la conexion a la memoria se reusan).
    Los tests lo reemplazan con app.dependency_overrides para no llamar al LLM."""
    from agente import Agente

    return Agente()


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    from agente import asegurar_bases

    inicio = time.perf_counter()
    resultado = asegurar_bases()
    obtener_agente()
    log_evento("api_iniciada", segundos_arranque=round(time.perf_counter() - inicio, 2), **resultado)
    yield
    log_evento("api_detenida")


app = FastAPI(
    title="AlquiHerramientas — Agente",
    description="Agente ReAct (LangGraph) con RAG, sensores y actuador sobre SQL, memoria por thread_id y guardrails.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)


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


@app.get("/health")
def health() -> dict:
    from pathlib import Path

    from agente import MAX_ITERACIONES, RUTA_MEMORIA

    return {"status": "ok", "memoria": Path(RUTA_MEMORIA).name, "max_iteraciones": MAX_ITERACIONES}


@app.post("/consultar", response_model=Respuesta)
def consultar(consulta: Consulta, agente=Depends(obtener_agente)) -> Respuesta:
    thread_id = consulta.thread_id or uuid.uuid4().hex[:12]
    inicio = time.perf_counter()

    # 1. Guardrails de entrada: si bloquean, el mensaje nunca llega al LLM (0 tokens).
    validacion = guardrails.validar_entrada(consulta.mensaje)
    if not validacion.permitido:
        metricas.registrar_bloqueo(validacion.motivo)
        log_evento(
            "consulta_bloqueada", logging.WARNING, thread_id=thread_id, motivo=validacion.motivo,
            tactica=validacion.tactica, largo_mensaje=len(consulta.mensaje),
            mensaje_enmascarado=guardrails.enmascarar_datos_personales(consulta.mensaje[:200]).texto,
        )
        raise HTTPException(status_code=400, detail={"motivo": validacion.motivo, "mensaje": validacion.detalle,
                                                     "thread_id": thread_id})

    # 2. Agente
    try:
        salida = agente.consultar(thread_id, consulta.mensaje)
    except Exception as e:  # el cliente recibe un 500 limpio; el detalle queda en el log
        latencia = (time.perf_counter() - inicio) * 1000
        metricas.registrar_error(latencia)
        log_evento("consulta_error", logging.ERROR, thread_id=thread_id, error=type(e).__name__,
                   detalle=str(e)[:300], latencia_ms=round(latencia, 1))
        raise HTTPException(status_code=500, detail={"motivo": "error_interno", "thread_id": thread_id}) from e

    # 3. Guardrail de salida: enmascarado de datos personales.
    enmascarado = guardrails.enmascarar_datos_personales(salida["respuesta"])
    latencia = (time.perf_counter() - inicio) * 1000
    tokens = salida.get("tokens", {"entrada": 0, "salida": 0})
    metricas.registrar_respuesta(latencia, salida["herramientas_usadas"], tokens["entrada"], tokens["salida"],
                                 enmascarado.enmascarado, salida["corte_por_limite"])
    log_evento(
        "consulta_respondida", thread_id=thread_id, latencia_ms=round(latencia, 1),
        herramientas=salida["herramientas_usadas"], iteraciones=salida["iteraciones"],
        corte_por_limite=salida["corte_por_limite"], tokens=tokens, datos_enmascarados=enmascarado.reemplazos,
        largo_mensaje=len(consulta.mensaje),
    )
    return Respuesta(
        thread_id=thread_id,
        respuesta=enmascarado.texto,
        herramientas_usadas=salida["herramientas_usadas"],
        iteraciones=salida["iteraciones"],
        corte_por_limite=salida["corte_por_limite"],
        datos_enmascarados=enmascarado.reemplazos,
        latencia_ms=round(latencia, 1),
        tokens=tokens,
        costo_estimado_usd=round(costo_usd(tokens["entrada"], tokens["salida"]), 6),
    )


@app.get("/estado/{thread_id}")
def estado(thread_id: str, agente=Depends(obtener_agente)) -> dict:
    datos = agente.estado(thread_id)
    if datos is None:
        raise HTTPException(status_code=404, detail={"motivo": "thread_inexistente", "thread_id": thread_id})
    # La memoria guarda los mensajes tal cual (el agente necesita el telefono para reservar);
    # lo que sale por HTTP pasa por el mismo enmascarado que las respuestas.
    for entrada in datos["historial"]:
        if "contenido" in entrada:
            entrada["contenido"] = guardrails.enmascarar_datos_personales(entrada["contenido"]).texto
        if "herramientas" in entrada:
            for h in entrada["herramientas"]:
                if "telefono" in h["argumentos"]:
                    h["argumentos"]["telefono"] = "[TELEFONO]"
    return datos


@app.get("/metricas")
def obtener_metricas() -> dict:
    return metricas.resumen()
