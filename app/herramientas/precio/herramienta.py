"""Slice precio — SENSOR del agente: precios y depósitos reales en SQL."""

from __future__ import annotations

from langchain_core.tools import tool

from app.herramientas.precio.consultas import consultar_precio as _consultar
from app.shared import sql


@tool
def consultar_precio(herramienta: sql.CodigoHerramienta, dias: int = 1) -> dict:
    """SENSOR. Consulta en la base SQL el precio por día, el total para la cantidad de días y el
    depósito de garantía de una herramienta. El total lo calcula el código, no el modelo.

    Cuándo usarla: "¿cuánto sale?", "¿cuánto es por 3 días?", "¿cuánto dejo de depósito?". Es la
    única fuente válida de precios: nunca estimes ni redondees un precio por tu cuenta.

    Args:
        herramienta: código del catálogo (taladro, hidrolavadora, lijadora, amoladora,
            sierra_circular, andamio, martillo_demoledor, hormigonera).
        dias: cantidad de días de alquiler (1 si el cliente no lo dice).

    Returns:
        dict con encontrado, nombre, precio_dia, dias_alquiler, precio_total y deposito_garantia
        (montos en pesos). Si la herramienta no existe o está inactiva, encontrado=False.
    """
    conn = sql.conectar()
    try:
        return _consultar(conn, herramienta, max(1, dias))
    finally:
        conn.close()
