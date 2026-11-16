"""
observabilidad.py - Logs JSON y metricas en memoria (TP Final, Parte C).

- Logs: una linea JSON por evento, a stdout y a logs/agente.jsonl. Nunca se loguea el mensaje
  crudo del cliente: solo su largo y una version enmascarada (guardrails.enmascarar_datos_personales),
  asi el log no termina siendo una base de telefonos y DNIs.
- Metricas: contadores en memoria que alimentan GET /metricas (consultas, errores, bloqueos,
  latencia promedio y p95, uso de herramientas, tokens y costo estimado). Se reinician con el
  proceso; el historico completo queda en logs/agente.jsonl.
- Costo: tokens reales (usage_metadata de Gemini) x tarifa por millon de tokens, configurable por
  .env. Las trazas detalladas por paso viven en LangSmith (LANGSMITH_TRACING=true).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIR_LOGS = RAIZ / "logs"

# Tarifas en USD por millon de tokens. Entrada: la misma tarifa de referencia de la Entrega 1
# (A.4). Salida: supuesto de orden de magnitud para un modelo flash. Las dos se pisan por .env
# y hay que verificarlas en la pagina de precios del proveedor; en el free tier el costo real es 0.
PRECIO_ENTRADA_USD_1M = float(os.getenv("PRECIO_ENTRADA_USD_1M", "0.30"))
PRECIO_SALIDA_USD_1M = float(os.getenv("PRECIO_SALIDA_USD_1M", "2.50"))


class _FormateadorJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "evento": record.getMessage(),
        }
        base.update(getattr(record, "campos", {}))
        return json.dumps(base, ensure_ascii=False, default=str)


def _crear_logger() -> logging.Logger:
    logger = logging.getLogger("alquiherramientas")
    if logger.handlers:  # uvicorn --reload o los tests importan el modulo mas de una vez
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formato = _FormateadorJSON()
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formato)
    logger.addHandler(consola)
    DIR_LOGS.mkdir(exist_ok=True)
    archivo = logging.FileHandler(DIR_LOGS / "agente.jsonl", encoding="utf-8")
    archivo.setFormatter(formato)
    logger.addHandler(archivo)
    return logger


logger = _crear_logger()


def log_evento(evento: str, nivel: int = logging.INFO, **campos) -> None:
    logger.log(nivel, evento, extra={"campos": campos})


def costo_usd(tokens_entrada: int, tokens_salida: int) -> float:
    return tokens_entrada / 1e6 * PRECIO_ENTRADA_USD_1M + tokens_salida / 1e6 * PRECIO_SALIDA_USD_1M


def _percentil(valores: list[float], p: float) -> float:
    """Percentil por rango mas cercano (sin numpy): con pocas muestras es mas honesto que interpolar."""
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = max(0, min(len(ordenados) - 1, int(round(p / 100 * len(ordenados) + 0.5)) - 1))
    return ordenados[indice]


class Metricas:
    """Contadores thread-safe: FastAPI corre los endpoints sincronos en un pool de threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.inicio = datetime.now(timezone.utc)
        self.consultas = 0
        self.respondidas = 0
        self.errores = 0
        self.bloqueos: dict[str, int] = {}
        self.herramientas: dict[str, int] = {}
        self.latencias_ms: list[float] = []
        self.tokens_entrada = 0
        self.tokens_salida = 0
        self.respuestas_enmascaradas = 0
        self.cortes_por_limite = 0

    def registrar_bloqueo(self, motivo: str) -> None:
        with self._lock:
            self.consultas += 1
            self.bloqueos[motivo] = self.bloqueos.get(motivo, 0) + 1

    def registrar_error(self, latencia_ms: float) -> None:
        with self._lock:
            self.consultas += 1
            self.errores += 1
            self.latencias_ms.append(latencia_ms)

    def registrar_respuesta(
        self,
        latencia_ms: float,
        herramientas: list[str],
        tokens_entrada: int,
        tokens_salida: int,
        enmascarada: bool,
        corte_por_limite: bool,
    ) -> None:
        with self._lock:
            self.consultas += 1
            self.respondidas += 1
            self.latencias_ms.append(latencia_ms)
            for h in herramientas:
                self.herramientas[h] = self.herramientas.get(h, 0) + 1
            self.tokens_entrada += tokens_entrada
            self.tokens_salida += tokens_salida
            self.respuestas_enmascaradas += int(enmascarada)
            self.cortes_por_limite += int(corte_por_limite)

    def resumen(self) -> dict:
        with self._lock:
            latencias = list(self.latencias_ms)
            costo = costo_usd(self.tokens_entrada, self.tokens_salida)
            return {
                "desde": self.inicio.isoformat(timespec="seconds"),
                "consultas": self.consultas,
                "respondidas": self.respondidas,
                "errores": self.errores,
                "bloqueos": {"total": sum(self.bloqueos.values()), "por_motivo": dict(self.bloqueos)},
                "latencia_ms": {
                    "promedio": round(sum(latencias) / len(latencias), 1) if latencias else 0.0,
                    "p95": round(_percentil(latencias, 95), 1),
                    "muestras": len(latencias),
                },
                "herramientas": dict(sorted(self.herramientas.items(), key=lambda kv: -kv[1])),
                "respuestas_enmascaradas": self.respuestas_enmascaradas,
                "cortes_por_limite_de_iteraciones": self.cortes_por_limite,
                "tokens": {"entrada": self.tokens_entrada, "salida": self.tokens_salida},
                "costo_estimado_usd": {
                    "total": round(costo, 6),
                    "por_consulta_respondida": round(costo / self.respondidas, 6) if self.respondidas else 0.0,
                    "tarifa_usd_por_millon": {"entrada": PRECIO_ENTRADA_USD_1M, "salida": PRECIO_SALIDA_USD_1M},
                },
            }
