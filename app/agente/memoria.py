"""Memoria del agente: SqliteSaver (langgraph-checkpoint-sqlite), una conversación por thread_id.

Es un archivo, no un dict en RAM: sobrevive reinicios del proceso. Está separado de la base de
negocio para no mezclar conversación con datos transaccionales.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.shared import config


def crear_checkpointer(ruta: Path | str | None = None):
    from langgraph.checkpoint.sqlite import SqliteSaver

    config.asegurar_directorios()
    # check_same_thread=False: FastAPI atiende cada request en un thread del pool; SqliteSaver
    # serializa los accesos con su propio lock.
    return SqliteSaver(sqlite3.connect(str(ruta or config.RUTA_MEMORIA), check_same_thread=False))
