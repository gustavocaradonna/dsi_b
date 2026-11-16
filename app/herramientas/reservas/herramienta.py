"""Slice reservas — ACTUADOR del agente: crea una reserva 'pendiente' en SQL."""

from __future__ import annotations

import re
from datetime import date

from langchain_core.tools import tool

from app.herramientas.reservas.consultas import crear_reserva as _crear
from app.shared import sql

MAX_DIAS_RESERVA = 30


def _fecha(valor: str, nombre: str) -> date:
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre} tiene que estar en formato YYYY-MM-DD (llegó {valor!r})") from None


@tool
def crear_reserva(
    herramienta: sql.CodigoHerramienta, fecha_inicio: str, fecha_fin: str, telefono: str, cantidad: int = 1
) -> dict:
    """ACTUADOR. Crea una reserva en estado 'pendiente' en la base SQL. Cambia el estado del negocio:
    ocupa stock para otros clientes.

    Cuándo usarla: SOLO si el cliente pidió reservar de forma explícita y ya dio herramienta, fecha
    de inicio, fecha de fin y teléfono de contacto. Si falta cualquiera de esos datos, NO la llames:
    pedile el dato al cliente. Antes, verificá el stock con consultar_disponibilidad.

    Args:
        herramienta: código del catálogo (taladro, hidrolavadora, lijadora, amoladora,
            sierra_circular, andamio, martillo_demoledor, hormigonera).
        fecha_inicio: primer día del alquiler, YYYY-MM-DD. No puede ser anterior a hoy.
        fecha_fin: último día del alquiler, YYYY-MM-DD. Máximo 30 días después del inicio.
        telefono: teléfono de contacto del cliente, tal como lo escribió (8 a 15 dígitos).
        cantidad: unidades a reservar (1 a 10).

    Returns:
        dict con reservado (bool). Si se reservó: reserva_id, nombre, cantidad, fechas, estado
        'pendiente', precio_total y deposito_garantia. Si no: motivo ('sin_stock',
        'herramienta_no_encontrada' o 'dato_invalido') y el detalle. El teléfono no se devuelve.
    """
    # Las validaciones viven en el código, no en el prompt: el actuador no confía en el LLM.
    try:
        inicio, fin = _fecha(fecha_inicio, "fecha_inicio"), _fecha(fecha_fin, "fecha_fin")
        digitos = re.sub(r"\D", "", telefono or "")
        if not 8 <= len(digitos) <= 15:
            raise ValueError("el teléfono tiene que tener entre 8 y 15 dígitos")
        if inicio < date.today():
            raise ValueError("la fecha de inicio ya pasó")
        if fin < inicio:
            raise ValueError("la fecha de fin es anterior a la de inicio")
        if (fin - inicio).days + 1 > MAX_DIAS_RESERVA:
            raise ValueError(f"el máximo es {MAX_DIAS_RESERVA} días por reserva")
        if not 1 <= cantidad <= 10:
            raise ValueError("la cantidad tiene que estar entre 1 y 10")
    except ValueError as e:
        return {"reservado": False, "motivo": "dato_invalido", "detalle": str(e)}

    conn = sql.conectar()
    try:
        return _crear(conn, digitos, herramienta, cantidad, inicio, fin)
    finally:
        conn.close()
