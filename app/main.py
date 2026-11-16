"""
Punto de entrada de la API: arma la aplicación registrando cada slice (composition root).

    uvicorn app.main:app --port 8000          (desde la raíz del repo)
    Documentación interactiva: http://localhost:8000/docs

Es el único archivo que conoce a todos los slices. Agregar un caso de uso = crear su carpeta en
features/ y sumar su router acá.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agente.servicio import obtener_agente
from app.features.consultar.endpoint import router as consultar
from app.features.estado.endpoint import router as estado
from app.features.health.endpoint import router as health
from app.features.metricas.endpoint import router as metricas
from app.herramientas.conocimiento.indice import asegurar_indice
from app.shared import http, sql
from app.shared.http import JSONUTF8
from app.shared.observabilidad import log_evento


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """En una máquina nueva construye lo que no viene en el repo (está en .gitignore): el índice
    vectorial y la base SQL. Si ya existen, no gasta ni un token."""
    inicio = time.perf_counter()
    chunks_creados = asegurar_indice()
    sql.conectar().close()
    obtener_agente()
    log_evento("api_iniciada", segundos_arranque=round(time.perf_counter() - inicio, 2), chunks_creados=chunks_creados)
    yield
    log_evento("api_detenida")


app = FastAPI(
    title="AlquiHerramientas — Agente",
    description="Agente ReAct (LangGraph) con RAG, sensores y actuador sobre SQL, memoria por thread_id y guardrails. "
    "Organizado con Vertical Slice Architecture.",
    version="2.0.0",
    lifespan=ciclo_de_vida,
    default_response_class=JSONUTF8,
)
http.registrar(app)
for router in (health, consultar, estado, metricas):
    app.include_router(router)
