"""
Lógica del slice consultar: un mensaje del cliente atraviesa, en este orden,

    1. guardrails de entrada (longitud, prompt injection) -> si bloquean, el mensaje nunca llega al LLM
    2. agente ReAct
    3. guardrail de salida (enmascarado de datos personales)
    4. métricas y log JSON
"""

from __future__ import annotations

import logging
import time
import uuid

from app.features.consultar.modelos import Consulta, Respuesta
from app.shared import guardrails
from app.shared.observabilidad import costo_usd, log_evento, metricas


class ConsultaBloqueada(Exception):
    def __init__(self, motivo: str, mensaje: str, thread_id: str):
        self.motivo, self.mensaje, self.thread_id = motivo, mensaje, thread_id


class ErrorDelAgente(Exception):
    def __init__(self, thread_id: str):
        self.thread_id = thread_id


def ejecutar(consulta: Consulta, agente) -> Respuesta:
    thread_id = consulta.thread_id or uuid.uuid4().hex[:12]
    inicio = time.perf_counter()

    validacion = guardrails.validar_entrada(consulta.mensaje)
    if not validacion.permitido:
        metricas.registrar_bloqueo(validacion.motivo)
        log_evento(
            "consulta_bloqueada", logging.WARNING, thread_id=thread_id, motivo=validacion.motivo,
            tactica=validacion.tactica, largo_mensaje=len(consulta.mensaje),
            mensaje_enmascarado=guardrails.enmascarar_datos_personales(consulta.mensaje[:200]).texto,
        )
        raise ConsultaBloqueada(validacion.motivo, validacion.detalle, thread_id)

    try:
        salida = agente.consultar(thread_id, consulta.mensaje)
    except Exception as e:  # el detalle queda en el log; al cliente le llega un 500 limpio
        latencia = (time.perf_counter() - inicio) * 1000
        metricas.registrar_error(latencia)
        log_evento("consulta_error", logging.ERROR, thread_id=thread_id, error=type(e).__name__,
                   detalle=str(e)[:300], latencia_ms=round(latencia, 1))
        raise ErrorDelAgente(thread_id) from e

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
