"""
pipeline_vectorial.py - Indice vectorial FAISS (Parte A, Clase 4).

Reemplaza "meter todo el catalogo en el prompt" (el problema que A.1 documenta) por una
memoria vectorial externa: embeddings de cada descripcion_semantica de
base_conocimiento.json, indexados con FAISS y persistidos en disco para no volver a pagar
tokens de embeddings en cada arranque (A.4, A.5).

Uso:
    python pipeline_vectorial.py                    # construye o recarga el indice, corre 3 consultas de prueba (A.4)
    python pipeline_vectorial.py --consulta "..."    # una consulta puntual
    python pipeline_vectorial.py --cosine-a-mano     # calculo de similitud coseno a mano + validacion NumPy (A.2)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

BASE_CONOCIMIENTO = "base_conocimiento.json"
DIR_INDICE = Path("faiss_index")
RUTA_INDICE = DIR_INDICE / "alquiherramientas.index"
RUTA_IDS = DIR_INDICE / "ids.json"

# --------------------------------------------------------------------------
# Cliente y embeddings (Gemini - reusa GEMINI_API_KEY, sin credenciales nuevas)
# --------------------------------------------------------------------------


def crear_cliente():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "ERROR: falta GEMINI_API_KEY.\n"
            "Copia .env.example a .env y completa la key de https://aistudio.google.com/apikey",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        from google import genai
    except ImportError:
        print("ERROR: falta instalar google-genai (pip install -r requirements.txt)", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=api_key)


def embed(cliente, textos: list[str]) -> np.ndarray:
    """Genera embeddings con Gemini y devuelve vectores L2-normalizados: con vectores
    normalizados, el producto interno (IndexFlatIP) es equivalente a similitud coseno."""
    modelo = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    respuesta = cliente.models.embed_content(model=modelo, contents=textos)
    vectores = np.array([e.values for e in respuesta.embeddings], dtype="float32")
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    return vectores / normas


def cargar_documentos(ruta: str = BASE_CONOCIMIENTO) -> list[dict]:
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Indice FAISS: construir o recargar (A.4) + prueba de volatilidad (A.5)
# --------------------------------------------------------------------------


def construir_o_cargar_indice(cliente):
    """Si el indice ya esta persistido en disco, lo recarga (0 tokens gastados).
    Si no existe -- primera vez, o porque se borro para simular un reinicio de servidor --
    regenera los embeddings de los 16 documentos y lo vuelve a persistir."""
    import faiss

    documentos = cargar_documentos()

    if RUTA_INDICE.exists() and RUTA_IDS.exists():
        print(f"[persistencia] Indice encontrado en disco: cargando desde {RUTA_INDICE} "
              f"(faiss.read_index, no se llama a la API de embeddings)")
        indice = faiss.read_index(str(RUTA_INDICE))
        with open(RUTA_IDS, encoding="utf-8") as fh:
            ids_guardados = json.load(fh)
        por_id = {d["id"]: d for d in documentos}
        documentos_ordenados = [por_id[i] for i in ids_guardados]
        return indice, documentos_ordenados

    print(f"[persistencia] No hay indice en disco: generando embeddings NUEVOS para "
          f"{len(documentos)} documentos (esto consume tokens de la API)...")
    textos = [d["descripcion_semantica"] for d in documentos]
    vectores = embed(cliente, textos)
    dimension = vectores.shape[1]

    indice = faiss.IndexFlatIP(dimension)
    indice.add(vectores)

    DIR_INDICE.mkdir(exist_ok=True)
    faiss.write_index(indice, str(RUTA_INDICE))
    with open(RUTA_IDS, "w", encoding="utf-8") as fh:
        json.dump([d["id"] for d in documentos], fh)
    print(f"[persistencia] Indice persistido en {RUTA_INDICE} ({dimension} dimensiones, "
          f"{indice.ntotal} vectores) -- faiss.write_index()")
    return indice, documentos


def buscar(cliente, indice, documentos, consulta: str, top_k: int = 3):
    """Top-K por similitud coseno (vectores normalizados + producto interno)."""
    vector_consulta = embed(cliente, [consulta])
    scores, posiciones = indice.search(vector_consulta, top_k)
    resultados = []
    for score, pos in zip(scores[0], posiciones[0]):
        if pos == -1:
            continue
        resultados.append((documentos[pos], float(score)))
    return resultados


CONSULTAS_PRUEBA = [
    "necesito algo para romper una pared de material",
    "quiero alquilar algo para limpiar el frente de mi casa",
    "cuanto tengo que dejar de seña si alquilo algo",
]


def _etiqueta(doc: dict) -> str:
    m = doc["metadatos"]
    return m.get("codigo_herramienta") or m.get("tipo_documento")


def correr_consultas_prueba(cliente, indice, documentos) -> None:
    for consulta in CONSULTAS_PRUEBA:
        print(f"\nConsulta: {consulta}")
        print("-" * 78)
        for doc, score in buscar(cliente, indice, documentos, consulta, top_k=3):
            resumen = " ".join(doc["descripcion_semantica"].split())[:90]
            print(f"  score={score:.4f}  {doc['id']} ({_etiqueta(doc)})  {resumen}...")


# --------------------------------------------------------------------------
# A.2 - Similitud coseno a mano, validada con NumPy
# --------------------------------------------------------------------------


def similitud_coseno(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def demo_similitud_a_mano() -> None:
    """Reduce el dominio a 2 ejes con sentido: potencia/uso pesado (eje X) vs.
    uso hogareno/liviano (eje Y). 3 documentos + 1 consulta, calculo en 3 pasos."""
    documentos_2d = {
        "martillo_demoledor (romper pared)": np.array([9.0, 1.0]),
        "taladro (perforar)": np.array([6.0, 7.0]),
        "lijadora (terminaciones finas)": np.array([2.0, 8.0]),
    }
    consulta = np.array([8.0, 2.0])  # "necesito romper una pared de material"

    print("Similitud coseno a mano (A.2)")
    print(f"Consulta: {consulta.tolist()}  ('necesito romper una pared de material')\n")
    for nombre, vector in documentos_2d.items():
        producto_punto = float(np.dot(consulta, vector))
        norma_consulta = float(np.linalg.norm(consulta))
        norma_doc = float(np.linalg.norm(vector))
        manual = producto_punto / (norma_consulta * norma_doc)
        validado = similitud_coseno(consulta, vector)
        assert abs(manual - validado) < 1e-9, "el calculo a mano no coincide con NumPy"
        print(f"  {nombre}  vector={vector.tolist()}")
        print(f"    paso 1  A . B              = {producto_punto:.4f}")
        print(f"    paso 2  ||A|| x ||B||      = {norma_consulta:.4f} x {norma_doc:.4f} = "
              f"{norma_consulta * norma_doc:.4f}")
        print(f"    paso 3  similitud = paso1/paso2 = {manual:.4f}   (validado con NumPy: {validado:.4f})")
    print()


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline vectorial FAISS - AlquiHerramientas")
    parser.add_argument(
        "--cosine-a-mano", action="store_true", help="Corre el calculo de A.2 (no llama a la API)"
    )
    parser.add_argument("--consulta", help="Corre una unica consulta top-K en vez del set de prueba")
    args = parser.parse_args()

    if args.cosine_a_mano:
        demo_similitud_a_mano()
        return

    cliente = crear_cliente()
    indice, documentos = construir_o_cargar_indice(cliente)

    if args.consulta:
        print(f"\nConsulta: {args.consulta}")
        print("-" * 78)
        for doc, score in buscar(cliente, indice, documentos, args.consulta, top_k=3):
            resumen = " ".join(doc["descripcion_semantica"].split())[:90]
            print(f"  score={score:.4f}  {doc['id']} ({_etiqueta(doc)})  {resumen}...")
        return

    correr_consultas_prueba(cliente, indice, documentos)


if __name__ == "__main__":
    main()
