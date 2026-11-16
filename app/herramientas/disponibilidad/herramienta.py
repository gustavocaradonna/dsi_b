"""Slice disponibilidad — SENSOR del agente: stock real en SQL."""

from __future__ import annotations

from datetime import date

from langchain_core.tools import tool

from app.herramientas.disponibilidad.consultas import consultar_disponibilidad as _consultar
from app.shared import sql


def _fecha(valor: str, nombre: str) -> date:
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre} tiene que estar en formato YYYY-MM-DD (llegó {valor!r})") from None


@tool
def consultar_disponibilidad(
    herramienta: sql.CodigoHerramienta, fecha_inicio: str, fecha_fin: str, cantidad: int = 1
) -> dict:
    """SENSOR. Consulta en la base SQL cuántas unidades de una herramienta están libres en una
    ventana de fechas, descontando las reservas pendientes, confirmadas y entregadas que se solapan.

    Cuándo usarla: "¿tienen X para el sábado?", "¿hay 2 andamios del 10 al 12?", y siempre antes de
    crear_reserva. Es la única fuente válida de stock: nunca supongas disponibilidad.

    Args:
        herramienta: código del catálogo (taladro, hidrolavadora, lijadora, amoladora,
            sierra_circular, andamio, martillo_demoledor, hormigonera).
        fecha_inicio: primer día del alquiler, formato YYYY-MM-DD.
        fecha_fin: último día del alquiler, formato YYYY-MM-DD (igual a fecha_inicio si es un solo día).
        cantidad: unidades que necesita el cliente (1 a 10).

    Returns:
        dict con encontrado, nombre, stock_total, disponibles, disponible (bool: alcanza para la
        cantidad pedida), precio_dia y las fechas consultadas. Si la herramienta no existe o está
        inactiva, encontrado=False.
    """
    inicio, fin = _fecha(fecha_inicio, "fecha_inicio"), _fecha(fecha_fin, "fecha_fin")
    conn = sql.conectar()
    try:
        return _consultar(conn, herramienta, inicio, fin, cantidad)
    finally:
        conn.close()
