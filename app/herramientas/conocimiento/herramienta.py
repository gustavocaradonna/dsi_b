"""Slice conocimiento — RETRIEVER del agente: el RAG de la Entrega 3 sobre fichas y políticas."""

from __future__ import annotations

from langchain_core.tools import tool

from app.herramientas.conocimiento.retriever import formatear, retriever


@tool
def buscar_informacion(consulta: str) -> str:
    """Busca en la base de conocimiento de AlquiHerramientas: fichas de herramientas (para qué sirve
    cada una, qué incluye, para qué NO sirve, cuidados) y políticas del local (depósito de garantía,
    requisitos para retirar, envío a domicilio, cancelación, horarios, roturas, seguridad).

    Cuándo usarla: cualquier pregunta sobre cómo funciona el local o sobre una herramienta que no sea
    stock ni precio. Si la pregunta tiene varias partes, llamala una vez por parte.
    Cuándo NO usarla: disponibilidad o stock (usá consultar_disponibilidad) y precios o montos de
    depósito (usá consultar_precio).

    Args:
        consulta: pregunta en lenguaje natural y autocontenida. Si se refiere a una herramienta,
            incluí su nombre (por ejemplo "¿hacen envío a domicilio de la amoladora?", no "¿me la traen?").

    Returns:
        Los documentos relevantes, cada uno con su id ([DOC-xxx]), tipo, categoría y texto completo.
        Devuelve "SIN_RESULTADOS" si ningún documento es relevante: en ese caso no hay información
        en la base y no se debe inventar una respuesta.
    """
    salida = retriever().invoke(consulta)
    return formatear(salida["contexto"]) if salida["contexto"] else "SIN_RESULTADOS"
