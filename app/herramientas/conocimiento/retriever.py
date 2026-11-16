"""
Retriever del slice conocimiento — el pipeline avanzado de la Entrega 3 sin el paso de generación:

    chunks k=8 (solo activos) -> juez LLM de relevancia (puntaje >= 6) -> documento padre completo

El documento padre es la mejora validada en la corrección de C.4 de la E3. La descomposición de
consulta del v2 no hace falta acá: el loop ReAct del agente ya llama a la herramienta una vez por
sub-pregunta.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from pydantic import BaseModel, Field

from app.herramientas.conocimiento import indice
from app.shared.llm import crear_llm

K_CANDIDATOS = 8
PUNTAJE_MINIMO = 6
MAX_CHUNKS = 6  # después se agrupan por documento padre (2 chunks por documento como mucho)
MAX_PADRES = 4


class JuicioFragmento(BaseModel):
    indice: int = Field(description="Numero del fragmento, tal como aparece entre corchetes")
    puntaje: int = Field(ge=0, le=10, description="0 = no sirve para responder, 10 = responde de forma directa")
    motivo: str = Field(description="Una frase corta que justifique el puntaje")


class JuiciosRelevancia(BaseModel):
    juicios: list[JuicioFragmento]


PROMPT_JUEZ = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Sos un juez de relevancia para el buscador de AlquiHerramientas (alquiler de herramientas).
Te doy la pregunta de un cliente y fragmentos numerados recuperados de la base de conocimiento.
Puntuá CADA fragmento de 0 a 10 según cuánto aporta información EXPLÍCITA para responder ESA pregunta:
- 9-10: contiene la respuesta directa.
- 6-8: aporta un dato necesario para una parte de la respuesta.
- 3-5: es del mismo tema pero no aporta un dato que la respuesta necesite.
- 0-2: no tiene relación, o habla de otra herramienta distinta a la pedida.
Si el cliente pide una herramienta que NO aparece en ningún fragmento, ningún fragmento de otra
herramienta merece más de 3. Devolvé un juicio por fragmento.""",
        ),
        ("human", "PREGUNTA: {pregunta}\n\nFRAGMENTOS:\n{fragmentos}"),
    ]
)


def _candidatos(pregunta: str) -> list[Document]:
    pares = indice.vectorstore().similarity_search_with_score(pregunta, k=K_CANDIDATOS, filter={"activo": True})
    salida = []
    for doc, distancia in pares:
        doc.metadata["distancia"] = round(float(distancia), 4)
        salida.append(doc)
    return salida


def _juez(llm):
    """Una sola llamada al juez por pregunta: puntúa los 8 fragmentos juntos."""
    cadena = PROMPT_JUEZ | llm.with_structured_output(JuiciosRelevancia)

    def rerankear(x: dict) -> list[Document]:
        candidatos: list[Document] = x["candidatos"]
        if not candidatos:
            return []
        fragmentos = "\n\n".join(f"[{i}] ({d.metadata.get('doc_id')}) {d.page_content}" for i, d in enumerate(candidatos))
        juicios = {j.indice: j for j in cadena.invoke({"pregunta": x["pregunta"], "fragmentos": fragmentos}).juicios}
        for i, d in enumerate(candidatos):
            d.metadata["puntaje_juez"] = juicios[i].puntaje if i in juicios else 0
        ordenados = sorted(candidatos, key=lambda d: -d.metadata["puntaje_juez"])  # el más relevante primero
        return [d for d in ordenados if d.metadata["puntaje_juez"] >= PUNTAJE_MINIMO][:MAX_CHUNKS]

    return RunnableLambda(rerankear).with_config(run_name="reranker_llm_juez")


def _documentos_padre(x: dict) -> list[Document]:
    """Chunks elegidos por el juez -> documentos completos, en el orden del juez."""
    fuente = indice.documentos()
    salida: dict[str, Document] = {}
    for chunk in x["chunks_seleccionados"]:
        doc_id = chunk.metadata["doc_id"]
        if doc_id not in salida:
            metadatos = dict(fuente[doc_id]["metadatos"])
            metadatos.update({"doc_id": doc_id, "puntaje_juez": chunk.metadata["puntaje_juez"]})
            salida[doc_id] = Document(page_content=fuente[doc_id]["descripcion_semantica"], metadata=metadatos)
    return list(salida.values())[:MAX_PADRES]


@lru_cache(maxsize=1)
def retriever():
    return (
        RunnableParallel(candidatos=RunnableLambda(_candidatos), pregunta=RunnablePassthrough())
        .assign(chunks_seleccionados=_juez(crear_llm()))
        .assign(contexto=RunnableLambda(_documentos_padre).with_config(run_name="expansion_documento_padre"))
    ).with_config(run_name="retriever_conocimiento")


def formatear(documentos: list[Document]) -> str:
    bloques = []
    for d in documentos:
        m = d.metadata
        etiqueta = " | ".join(
            str(v) for v in (m.get("doc_id"), m.get("tipo_documento"), m.get("categoria"), m.get("codigo_herramienta")) if v
        )
        bloques.append(f"[{etiqueta}]\n{d.page_content}")
    return "\n\n---\n\n".join(bloques)
