"""
Índice vectorial del slice conocimiento: chunks de base_conocimiento.json en ChromaDB.

Mismos parámetros que el RAG avanzado de la Entrega 3 (entregas/entrega_3/rag_pipeline.py):
chunks de 500 caracteres con 100 de solapamiento, colección "alquiherramientas_chunks", distancia
coseno y los embeddings de Gemini sin task_type (los mismos de la Entrega 2).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.shared import config

BASE_CONOCIMIENTO = Path(__file__).resolve().parent / "base_conocimiento.json"
NOMBRE_COLECCION = "alquiherramientas_chunks"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


class EmbeddingsGemini(Embeddings):
    """Adaptador LangChain sobre la EmbeddingFunction de Gemini que trae chromadb.

    No se usa GoogleGenerativeAIEmbeddings porque manda un task_type (RETRIEVAL_QUERY /
    RETRIEVAL_DOCUMENT) con el que la base de las Entregas 2 y 3 no se indexó: las distancias
    dejarían de ser comparables con las medidas en esas entregas."""

    def __init__(self) -> None:
        from chromadb.utils.embedding_functions import GoogleGeminiEmbeddingFunction

        self._ef = GoogleGeminiEmbeddingFunction(model_name=config.GEMINI_EMBEDDING_MODEL)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in v] for v in self._ef(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def documentos() -> dict[str, dict]:
    """La fuente de verdad: base_conocimiento.json, indexado por id de documento."""
    with open(BASE_CONOCIMIENTO, encoding="utf-8") as fh:
        return {d["id"]: d for d in json.load(fh)}


@lru_cache(maxsize=1)
def vectorstore():
    from langchain_chroma import Chroma

    config.verificar_api_key()
    config.asegurar_directorios()
    return Chroma(
        collection_name=NOMBRE_COLECCION,
        persist_directory=str(config.RUTA_CHROMA),
        embedding_function=EmbeddingsGemini(),
        collection_metadata={"hnsw:space": "cosine"},
    )


def asegurar_indice() -> int:
    """Idempotente: si la colección ya tiene chunks no hace nada (0 tokens de embeddings). En una
    máquina nueva la construye desde base_conocimiento.json. Devuelve cuántos chunks creó."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    vs = vectorstore()
    if vs._collection.count() > 0:
        return 0
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=["\n\n", "\n", ". ", ", ", " ", ""]
    )
    chunks, ids = [], []
    for doc_id, d in documentos().items():
        partes = splitter.split_text(d["descripcion_semantica"])
        for i, texto in enumerate(partes):
            metadatos = dict(d["metadatos"])
            metadatos.update({"doc_id": doc_id, "chunk": i, "chunks_del_doc": len(partes)})
            chunks.append(Document(page_content=texto, metadata=metadatos))
            ids.append(f"{doc_id}#c{i}")
    vs.add_documents(chunks, ids=ids)
    return len(chunks)
