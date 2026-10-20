"""
vector_db.py - ChromaDB persistente, filtrado hibrido y Killer Queries (Parte B, Clase 5).

Migra la base de A.3 de FAISS (indice de vectores puro, sin metadatos ni filtro) a ChromaDB
(coleccion persistente, con metadatos y filtrado nativo por where). Misma fuente de verdad
que FAISS: base_conocimiento.json. Mismos embeddings: Gemini (google_gemini, la
EmbeddingFunction que trae chromadb).

Uso:
    python vector_db.py --cargar                         # upsert de los 16 documentos (B.1, idempotente)
    python vector_db.py --buscar "..." --categoria X      # busqueda hibrida ad-hoc (B.4)
    python vector_db.py --evento-en-caliente              # demo de upsert en caliente (B.3)
    python vector_db.py --killer-queries                  # corre B.6 y escribe resultados_killer_queries.md
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Rutas absolutas respecto de este archivo (no del directorio actual): asi entrega_3/ puede
# importar este modulo y apuntar a la MISMA base, en vez de crear un chroma_db vacio al lado.
RAIZ = Path(__file__).resolve().parent
BASE_CONOCIMIENTO = str(RAIZ / "base_conocimiento.json")
RUTA_CHROMA = str(RAIZ / "chroma_db")
NOMBRE_COLECCION = "alquiherramientas"

# --------------------------------------------------------------------------
# Cliente, coleccion y embeddings (mismo proveedor que pipeline_vectorial.py)
# --------------------------------------------------------------------------


def _embedding_function():
    from chromadb.utils.embedding_functions import GoogleGeminiEmbeddingFunction

    modelo = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    return GoogleGeminiEmbeddingFunction(model_name=modelo)


def obtener_coleccion():
    """PersistentClient (B.1): la coleccion vive en disco, no en RAM volatil."""
    load_dotenv(RAIZ / ".env")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("ERROR: falta GEMINI_API_KEY en .env")

    import chromadb

    cliente = chromadb.PersistentClient(path=RUTA_CHROMA)
    return cliente.get_or_create_collection(
        name=NOMBRE_COLECCION,
        embedding_function=_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def cargar_base(coleccion, ruta: str = BASE_CONOCIMIENTO) -> int:
    """Ingesta con upsert (B.1): re-ejecutar no duplica, solo actualiza."""
    with open(ruta, encoding="utf-8") as fh:
        documentos = json.load(fh)

    coleccion.upsert(
        ids=[d["id"] for d in documentos],
        documents=[d["descripcion_semantica"] for d in documentos],
        metadatas=[d["metadatos"] for d in documentos],
    )
    return len(documentos)


# Umbral de aceptacion (distancia coseno). Recalibrado en la Entrega 3 con 40 consultas
# nuevas separadas en calibracion / validacion held-out: ver entrega_3/calibracion_umbral.py
# y entrega_3/resultados_calibracion.md. (El 0.32 original de la Entrega 2 se habia elegido
# con las mismas 3 consultas que despues lo aprobaban, y rechazaba 6 de 24 preguntas
# legitimas.) Positivas y negativas "cercanas al dominio" se solapan en 0.31-0.35: ningun
# umbral las separa del todo, asi que se prioriza no perder preguntas validas y las
# negativas cercanas que pasan las frena la capa de generacion (guardrail + reranking).
UMBRAL_DISTANCIA = 0.36

# --------------------------------------------------------------------------
# B.4 - CLI de busqueda hibrida: semantica (query_texts) + filtro nativo (where)
# --------------------------------------------------------------------------


def buscar_alquiherramientas(
    coleccion,
    query_semantica: str,
    categoria: str | None = None,
    tipo_documento: str | None = None,
    codigo_herramienta: str | None = None,
    solo_activos: bool = True,
    n_resultados: int = 5,
    umbral_distancia: float | None = UMBRAL_DISTANCIA,
):
    """Busqueda hibrida: NUNCA post-filtering en Python. El filtro va dentro del where,
    asi Chroma calcula similitud solo sobre lo que va a devolver, no sobre todo y despues
    descarta (eso es exactamente lo que el warning de B.4 prohibe).

    El umbral de aceptacion SI se aplica despues de la query, y es deliberado: Chroma no
    tiene un filtro nativo por distancia, y el umbral no es un filtro de negocio sino la
    regla "si nada es lo bastante parecido, no hay respuesta". Vive DENTRO de la funcion
    (correccion de la Entrega 2) para que ningun llamador pueda saltearselo; un resultado
    vacio significa "no tengo esa informacion". umbral_distancia=None lo desactiva (solo
    para calibrar, ver entrega_3/calibracion_umbral.py)."""
    condiciones = []
    if solo_activos:
        condiciones.append({"activo": {"$eq": True}})
    if categoria:
        condiciones.append({"categoria": {"$eq": categoria}})
    if tipo_documento:
        condiciones.append({"tipo_documento": {"$eq": tipo_documento}})
    if codigo_herramienta:
        condiciones.append({"codigo_herramienta": {"$eq": codigo_herramienta}})

    where = None
    if len(condiciones) == 1:
        where = condiciones[0]
    elif len(condiciones) > 1:
        where = {"$and": condiciones}

    resultado = coleccion.query(
        query_texts=[query_semantica],
        n_results=n_resultados,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    if umbral_distancia is None:
        return resultado

    # Chroma devuelve las distancias ordenadas de menor a mayor: alcanza con cortar la lista.
    distancias = resultado["distances"][0]
    corte = sum(d <= umbral_distancia for d in distancias)
    for clave in ("ids", "documents", "metadatas", "distances"):
        resultado[clave] = [resultado[clave][0][:corte]]
    return resultado


def _imprimir_resultado(resultado) -> None:
    ids = resultado["ids"][0]
    documentos = resultado["documents"][0]
    metadatas = resultado["metadatas"][0]
    distancias = resultado["distances"][0]
    if not ids:
        print("  (sin resultados: nada paso el filtro o la base esta vacia)")
        return
    for doc_id, doc, meta, dist in zip(ids, documentos, metadatas, distancias):
        etiqueta = meta.get("codigo_herramienta") or meta.get("tipo_documento")
        resumen = " ".join(doc.split())[:90]
        print(f"  distancia={dist:.4f}  {doc_id} ({etiqueta}, activo={meta.get('activo')})  {resumen}...")


# --------------------------------------------------------------------------
# B.3 - Evento de negocio en caliente
# --------------------------------------------------------------------------


def demo_evento_en_caliente(coleccion) -> None:
    """Simula que la sierra circular entra a service (se rompio) y despues vuelve a estar
    activa -- un cambio de estado real, verificado con get(), no relanzando toda la carga."""
    doc_id = "DOC-006"
    original = coleccion.get(ids=[doc_id], include=["documents", "metadatas"])
    texto = original["documents"][0]
    metadatos = dict(original["metadatas"][0])

    print(f"Estado antes:  activo={metadatos['activo']}")

    metadatos["activo"] = False
    coleccion.upsert(ids=[doc_id], documents=[texto], metadatas=[metadatos])
    verificacion = coleccion.get(ids=[doc_id], include=["metadatas"])
    print(f"Estado despues del upsert (rota, entra a service): activo={verificacion['metadatas'][0]['activo']}")

    metadatos["activo"] = True
    coleccion.upsert(ids=[doc_id], documents=[texto], metadatas=[metadatos])
    verificacion = coleccion.get(ids=[doc_id], include=["metadatas"])
    print(f"Estado despues de la reparacion: activo={verificacion['metadatas'][0]['activo']}")
    print(
        "\nPor que upsert y no add/update: add() falla si el id ya existe (rompe la "
        "re-ejecucion idempotente de B.1); update() falla si el id NO existe todavia. "
        "upsert() cubre los dos casos con una sola llamada, que es exactamente lo que hace "
        "falta para un evento de negocio que puede ser la primera vez o la enesima."
    )


# --------------------------------------------------------------------------
# B.6 - Killer Queries
# --------------------------------------------------------------------------

KILLER_QUERIES = [
    {
        "descripcion": "Poder semantico: jerga regional sin palabras exactas del documento",
        "query": "tengo que picar los cascotes de un piso viejo antes de embaldosar de nuevo",
        "filtros": {},
        "esperado": "DOC-008 (martillo_demoledor) arriba, aunque 'cascotes' y 'embaldosar' no estan en su texto",
    },
    {
        "descripcion": "El metadato salva el dia: sin filtro el taladro de baja queda pegado al activo "
        "(distancias casi identicas), el filtro lo saca del todo",
        "query": "necesito un taladro percutor para el sabado",
        "filtros": {"solo_activos": True},
        "esperado": "Sin filtro, DOC-002 (descontinuado) queda en el top-2 a una distancia casi identica "
        "a DOC-001; con el where, DOC-002 desaparece de los resultados",
    },
    {
        "descripcion": "Prueba de estres: consulta fuera de catalogo",
        "query": "necesito alquilar un generador electrico portatil",
        "filtros": {},
        # Con el umbral recalibrado (0.36) esta consulta (0.3507) cae en la zona de
        # solapamiento y la base vectorial sola NO la rechaza: la frena el guardrail del
        # prompt del RAG (entrega_3/rag_pipeline.py, matriz A.3, fila "fuera de dominio").
        "esperado": "Ninguna distancia deberia superar el umbral de aceptacion -> 'no tengo eso'",
    },
]


def correr_killer_queries(coleccion, ruta_md: str = "resultados_killer_queries.md") -> None:
    lineas = [
        "# Resultados de las Killer Queries (B.6)",
        "",
        f"**Umbral de aceptacion (distancia coseno):** {UMBRAL_DISTANCIA} — ver C.2 en "
        "informe_entrega2.md.  ",
        f"**Fecha de corrida:** {date.today().isoformat()}",
        "",
        "| # | Consulta | Que pone a prueba | Resultado esperado | Resultado real | Paso |",
        "|---|---|---|---|---|---|",
    ]

    for i, kq in enumerate(KILLER_QUERIES, start=1):
        print(f"\n[{i}] {kq['descripcion']}")
        print(f"    query: {kq['query']}")

        # Para la Killer Query 2 mostramos primero la semantica cruda (sin filtro) y
        # despues el resultado con el filtro puesto -- ese contraste ES la prueba.
        if i == 2:
            crudo = buscar_alquiherramientas(
                coleccion, kq["query"], solo_activos=False, n_resultados=3, umbral_distancia=None
            )
            print("  Sin filtro (semantica cruda):")
            _imprimir_resultado(crudo)

        resultado = buscar_alquiherramientas(coleccion, kq["query"], n_resultados=3, **kq["filtros"])
        print("  Con filtro (lo que realmente responde el sistema):")
        _imprimir_resultado(resultado)

        ids = resultado["ids"][0]
        distancias = resultado["distances"][0]

        if i == 1:
            paso = bool(ids) and ids[0] == "DOC-008"
            resultado_real = f"1ro: `{ids[0]}` (dist {distancias[0]:.4f})" if ids else "sin resultados"
        elif i == 2:
            paso = "DOC-002" not in ids
            resultado_real = (
                f"con filtro: `{ids}` (activos={[d['activo'] for d in resultado['metadatas'][0]]}); "
                f"sin filtro DOC-002 aparecia en el top-2 (dist {crudo['distances'][0][1]:.4f} vs. "
                f"{crudo['distances'][0][0]:.4f} de DOC-001)"
            )
        else:
            # El umbral ya lo aplico buscar_alquiherramientas(): pasa si la funcion no devolvio
            # nada. La distancia cruda se pide aparte solo para documentarla.
            paso = not ids
            crudo = buscar_alquiherramientas(coleccion, kq["query"], n_resultados=1, umbral_distancia=None)
            mejor = f"{crudo['distances'][0][0]:.4f} ({crudo['ids'][0][0]})"
            resultado_real = (
                f"la funcion no devolvio resultados (mejor distancia cruda {mejor})"
                if not ids
                else f"devolvio `{ids}` (mejor distancia {distancias[0]:.4f})"
            )

        lineas.append(
            f"| {i} | {kq['query']} | {kq['descripcion']} | {kq['esperado']} | "
            f"{resultado_real} | {'Si' if paso else 'No'} |"
        )

    with open(ruta_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")
    print(f"\nTabla escrita en {ruta_md}")


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="ChromaDB - AlquiHerramientas")
    parser.add_argument("--cargar", action="store_true", help="Upsert de base_conocimiento.json (B.1)")
    parser.add_argument("--buscar", help="Consulta semantica ad-hoc")
    parser.add_argument("--categoria")
    parser.add_argument("--tipo-documento")
    parser.add_argument("--codigo-herramienta")
    parser.add_argument("--incluir-inactivos", action="store_true")
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--evento-en-caliente", action="store_true", help="Demo de B.3")
    parser.add_argument("--killer-queries", action="store_true", help="Corre B.6")
    args = parser.parse_args()

    coleccion = obtener_coleccion()
    if coleccion.count() == 0 or args.cargar:
        n = cargar_base(coleccion)
        print(f"Coleccion '{NOMBRE_COLECCION}' cargada: {n} documentos (upsert).")
        if args.cargar and not (args.buscar or args.evento_en_caliente or args.killer_queries):
            return

    if args.evento_en_caliente:
        demo_evento_en_caliente(coleccion)
        return

    if args.killer_queries:
        correr_killer_queries(coleccion)
        return

    if args.buscar:
        resultado = buscar_alquiherramientas(
            coleccion,
            args.buscar,
            categoria=args.categoria,
            tipo_documento=args.tipo_documento,
            codigo_herramienta=args.codigo_herramienta,
            solo_activos=not args.incluir_inactivos,
            n_resultados=args.n,
        )
        print(f"\nConsulta: {args.buscar}")
        print("-" * 78)
        _imprimir_resultado(resultado)
        return

    print(f"Coleccion '{NOMBRE_COLECCION}': {coleccion.count()} documentos. "
          f"Usa --buscar, --evento-en-caliente o --killer-queries.")


if __name__ == "__main__":
    main()
