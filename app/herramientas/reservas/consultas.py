"""Acceso a datos del slice reservas: escribe una reserva 'pendiente' SOLO si hay stock real.

El chequeo de stock se hace acá adentro, en la misma conexión que escribe, y no llamando al slice
disponibilidad: los slices no se importan entre sí, y el actuador no puede depender de que el LLM
haya consultado el stock antes.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from app.shared import sql


def _upsert_cliente(conn: sqlite3.Connection, telefono: str) -> int:
    conn.execute("INSERT INTO clientes (telefono) VALUES (?) ON CONFLICT(telefono) DO NOTHING", (telefono,))
    return conn.execute("SELECT id FROM clientes WHERE telefono = ?", (telefono,)).fetchone()["id"]


def crear_reserva(
    conn: sqlite3.Connection, telefono: str, herramienta: str, cantidad: int, fecha_inicio: date, fecha_fin: date
) -> dict:
    h = sql.obtener_herramienta(conn, herramienta)
    if h is None:
        return {"reservado": False, "motivo": "herramienta_no_encontrada", "herramienta": herramienta}
    ini, fin = fecha_inicio.isoformat(), fecha_fin.isoformat()
    libres = h["stock_total"] - sql.stock_ocupado(conn, h["id"], ini, fin)
    if libres < cantidad:
        return {"reservado": False, "motivo": "sin_stock", "herramienta": herramienta, "disponibles": max(libres, 0)}

    cliente_id = _upsert_cliente(conn, telefono)
    precio_total = round(h["precio_dia"] * ((fecha_fin - fecha_inicio).days + 1), 2)
    cursor = conn.execute(
        "INSERT INTO reservas (cliente_id, herramienta_id, cantidad, fecha_inicio, fecha_fin, estado, precio_total)"
        " VALUES (?, ?, ?, ?, ?, 'pendiente', ?)",
        (cliente_id, h["id"], cantidad, ini, fin, precio_total),
    )
    conn.commit()
    return {
        "reservado": True,
        "reserva_id": cursor.lastrowid,
        "herramienta": herramienta,
        "nombre": h["nombre"],
        "cantidad": cantidad,
        "fecha_inicio": ini,
        "fecha_fin": fin,
        "estado": "pendiente",
        "precio_total": precio_total,
        "deposito_garantia": h["deposito_garantia"],
    }
