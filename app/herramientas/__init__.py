"""
Slices de herramientas del agente: una capacidad = una carpeta, con su tool y su acceso a datos.

    conocimiento/    buscar_informacion        RETRIEVER  (RAG de la E3 sobre ChromaDB)
    disponibilidad/  consultar_disponibilidad  SENSOR     (stock en SQL)
    precio/          consultar_precio          SENSOR     (precio y depósito en SQL)
    reservas/        crear_reserva             ACTUADOR   (escribe una reserva en SQL)

Para sumar una capacidad nueva: crear su carpeta y agregarla a HERRAMIENTAS. Nada más cambia.
"""

from app.herramientas.conocimiento.herramienta import buscar_informacion
from app.herramientas.disponibilidad.herramienta import consultar_disponibilidad
from app.herramientas.precio.herramienta import consultar_precio
from app.herramientas.reservas.herramienta import crear_reserva

HERRAMIENTAS = [buscar_informacion, consultar_disponibilidad, consultar_precio, crear_reserva]
