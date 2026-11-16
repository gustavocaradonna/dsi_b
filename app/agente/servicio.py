"""Interfaz del agente para los slices HTTP: consultar (un turno) y estado (historial)."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agente.grafo import construir_grafo
from app.agente.memoria import crear_checkpointer
from app.shared import config


class Agente:
    def __init__(self, grafo=None, max_iteraciones: int = config.MAX_ITERACIONES):
        self.max_iteraciones = max_iteraciones
        self.grafo = grafo or construir_grafo(crear_checkpointer(), max_iteraciones=max_iteraciones)

    def _config(self, thread_id: str) -> dict:
        # recursion_limit: segunda barrera por si el contador fallara (cada iteración son 3 pasos).
        return {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 3 * self.max_iteraciones + 5,
            "run_name": "agente_alquiherramientas",
            "tags": ["tp_final"],
            "metadata": {"thread_id": thread_id},
        }

    def consultar(self, thread_id: str, mensaje: str) -> dict:
        config_run = self._config(thread_id)
        previos = len(self.grafo.get_state(config_run).values.get("messages", []))
        with get_usage_metadata_callback() as cb:
            estado = self.grafo.invoke({"messages": [HumanMessage(mensaje)], "iteraciones": 0}, config_run)
        nuevos = estado["messages"][previos:]
        final = estado["messages"][-1]
        return {
            "thread_id": thread_id,
            "respuesta": final.text if hasattr(final, "text") else str(final.content),
            "herramientas_usadas": [tc["name"] for m in nuevos if isinstance(m, AIMessage) for tc in (m.tool_calls or [])],
            "iteraciones": estado.get("iteraciones", 0),
            "corte_por_limite": getattr(final, "name", None) == "limite_iteraciones",
            "tokens": {
                "entrada": sum(u.get("input_tokens", 0) for u in cb.usage_metadata.values()),
                "salida": sum(u.get("output_tokens", 0) for u in cb.usage_metadata.values()),
            },
        }

    def estado(self, thread_id: str) -> dict | None:
        mensajes = self.grafo.get_state(self._config(thread_id)).values.get("messages", [])
        if not mensajes:
            return None
        historial = []
        for m in mensajes:
            if isinstance(m, HumanMessage):
                historial.append({"rol": "cliente", "contenido": m.text})
            elif isinstance(m, AIMessage) and m.tool_calls:
                historial.append({"rol": "agente", "herramientas": [
                    {"nombre": tc["name"], "argumentos": tc["args"]} for tc in m.tool_calls]})
            elif isinstance(m, AIMessage):
                historial.append({"rol": "agente", "contenido": m.text})
            elif isinstance(m, ToolMessage):
                historial.append({"rol": "herramienta", "nombre": m.name, "contenido": str(m.content)[:500]})
        return {
            "thread_id": thread_id,
            "mensajes": len(mensajes),
            "turnos_del_cliente": sum(isinstance(m, HumanMessage) for m in mensajes),
            "historial": historial,
        }


@lru_cache(maxsize=1)
def obtener_agente() -> Agente:
    """Un solo agente por proceso. Los slices lo reciben con Depends(obtener_agente), y los tests
    lo reemplazan con app.dependency_overrides para no llamar al LLM."""
    return Agente()
