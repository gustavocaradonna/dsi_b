"""Acceso a datos del slice disponibilidad: stock libre de una herramienta en una ventana de fechas."""

from __future__ import annotations

import sqlite3
from datetime import date

from app.shared import sql


def consultar_disponibilidad(
    conn: sqlite3.Connection, herramienta: str, fecha_inicio: date, fecha_fin: date, cantidad: int = 1
) -> dict:
    h = sql.obtener_herramienta(conn, herramienta)
    if h is None:
        return {"encontrado": False, "herramienta": herramienta}
    ini, fin = fecha_inicio.isoformat(), fecha_fin.isoformat()
    libres = h["stock_total"] - sql.stock_ocupado(conn, h["id"], ini, fin)
    return {
        "encontrado": True,
        "herramienta": herramienta,
        "nombre": h["nombre"],
        "stock_total": h["stock_total"],
        "disponibles": max(libres, 0),
        "disponible": libres >= cantidad,
        "precio_dia": h["precio_dia"],
        "fecha_inicio": ini,
        "fecha_fin": fin,
    }
