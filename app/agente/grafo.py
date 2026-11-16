"""
Grafo ReAct explícito (no el prebuilt), para que el límite de iteraciones se vea en el código:

    START -> agente --(pide herramientas y quedan iteraciones)--> contar -> herramientas -> agente
                    --(pide herramientas y se agotó el límite)--> limite -> END   (mensaje fijo)
                    --(responde sin pedir herramientas)--------------------------> END
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import AIMessage, AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.agente.prompt import MENSAJE_LIMITE, prompt_sistema
from app.herramientas import HERRAMIENTAS
from app.shared import config


class EstadoAgente(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    iteraciones: int  # rondas agente -> herramientas en el turno actual; se reinicia en cada mensaje


def construir_grafo(checkpointer=None, llm=None, max_iteraciones: int = config.MAX_ITERACIONES):
    """llm se puede inyectar (los tests usan un modelo falso); por defecto, Gemini con las herramientas."""
    if llm is None:
        from app.shared.llm import crear_llm

        llm = crear_llm()
    modelo = llm.bind_tools(HERRAMIENTAS)

    def nodo_agente(estado: EstadoAgente) -> dict:
        return {"messages": [modelo.invoke([prompt_sistema(), *estado["messages"]])]}

    def nodo_limite(estado: EstadoAgente) -> dict:
        return {"messages": [AIMessage(MENSAJE_LIMITE, name="limite_iteraciones")]}

    def contar_iteracion(estado: EstadoAgente) -> dict:
        return {"iteraciones": estado.get("iteraciones", 0) + 1}

    def ruta(estado: EstadoAgente) -> str:
        if not getattr(estado["messages"][-1], "tool_calls", None):
            return END
        return "limite" if estado.get("iteraciones", 0) >= max_iteraciones else "contar"

    grafo = StateGraph(EstadoAgente)
    grafo.add_node("agente", nodo_agente)
    grafo.add_node("contar", contar_iteracion)
    grafo.add_node("herramientas", ToolNode(HERRAMIENTAS, handle_tool_errors=True))
    grafo.add_node("limite", nodo_limite)
    grafo.add_edge(START, "agente")
    grafo.add_conditional_edges("agente", ruta, {"contar": "contar", "limite": "limite", END: END})
    grafo.add_edge("contar", "herramientas")
    grafo.add_edge("herramientas", "agente")
    grafo.add_edge("limite", END)
    return grafo.compile(checkpointer=checkpointer)
