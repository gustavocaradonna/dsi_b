"""Acceso a datos del slice precio: precio por día, total y depósito. El total lo calcula el código."""

from __future__ import annotations

import sqlite3

from app.shared import sql


def consultar_precio(conn: sqlite3.Connection, herramienta: str, dias: int) -> dict:
    h = sql.obtener_herramienta(conn, herramienta)
    if h is None:
        return {"encontrado": False, "herramienta": herramienta}
    return {
        "encontrado": True,
        "herramienta": herramienta,
        "nombre": h["nombre"],
        "precio_dia": h["precio_dia"],
        "deposito_garantia": h["deposito_garantia"],
        "dias_alquiler": dias,
        "precio_total": round(h["precio_dia"] * dias, 2),
    }
