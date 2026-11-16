"""
Configuración: un solo lugar para rutas y variables de entorno.

Todas las rutas se resuelven respecto de la raíz del repo (no del directorio desde donde se lanza
uvicorn). Los datos que genera el sistema al correr (base vectorial, base SQL, memoria, logs) viven
en DIR_DATOS, que está en .gitignore y se puede mover con la variable DIR_DATOS.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")  # antes de importar LangChain: toma GEMINI_* y LANGSMITH_*

DIR_DATOS = RAIZ / os.getenv("DIR_DATOS", "data")
RUTA_CHROMA = DIR_DATOS / "chroma_db"
RUTA_DB_NEGOCIO = DIR_DATOS / "alquiherramientas.db"
RUTA_MEMORIA = DIR_DATOS / os.getenv("RUTA_MEMORIA", "memoria_agente.sqlite")
DIR_LOGS = DIR_DATOS / "logs"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0"))
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

MAX_ITERACIONES = int(os.getenv("MAX_ITERACIONES", "5"))  # rondas agente -> herramientas por mensaje

# USD por millón de tokens. Coinciden con la tabla de precios que usa LangSmith para el modelo.
PRECIO_ENTRADA_USD_1M = float(os.getenv("PRECIO_ENTRADA_USD_1M", "0.30"))
PRECIO_SALIDA_USD_1M = float(os.getenv("PRECIO_SALIDA_USD_1M", "2.50"))


def asegurar_directorios() -> None:
    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    DIR_LOGS.mkdir(parents=True, exist_ok=True)


def verificar_api_key() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("ERROR: falta GEMINI_API_KEY en .env (ver .env.example)")
