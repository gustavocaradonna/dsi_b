"""
etl_purga.py - ETL y purga semantica sobre un lote nuevo de documentos (Parte B, B.5).

Simula lo que pasa cuando alguien intenta sumar documentos nuevos a la Base de Conocimiento
a mano: llegan con inconsistencias de formato, un choque de IDs, y un par que en realidad ya
estan cubiertos por un documento existente, dicho con otras palabras. Este script normaliza
claves y tipos, resuelve el choque de IDs, y purga los casi-duplicados comparandolos por
embeddings contra base_conocimiento.json (la fuente de verdad) -- nunca contra un DISTINCT de
texto exacto, que no encontraria ninguno de estos casos porque ni el id ni el texto coinciden.

Uso:
    python etl_purga.py
"""

from __future__ import annotations

import json
import os

import numpy as np
from dotenv import load_dotenv

BASE_CONOCIMIENTO = "base_conocimiento.json"

# Mucho mas estricto que el umbral de busqueda de B.6/C.2 (0.32): ahi buscamos "relevante",
# aca buscamos "es el mismo documento con otras palabras". Calibrado con distancias reales:
# los 2 casi-duplicados a proposito de este lote miden 0.1673 y 0.1920; el contenido
# genuinamente nuevo mide 0.2739 en adelante. 0.22 separa limpio ambos grupos (ver
# informe_entrega2.md, B.5).
UMBRAL_DUPLICADO = 0.22

# --------------------------------------------------------------------------
# El lote sucio: alguien intento agregar estos 6 documentos "a mano"
# --------------------------------------------------------------------------

DATOS_CRUDOS: list[dict] = [
    # Casi-duplicado 1: mismo concepto que DOC-004 (lijadora), otra jerga, otro id.
    {
        "id": "DOC-017",
        "descripcion_semantica": "Lija electrica orbital para preparar madera antes de pintar, sacar "
        "una mano vieja de pintura y dejar los bordes de un mueble bien lisos.",
        "metadatos": {
            "categoria": "electrico",
            "activo": True,
            "tipo_documento": "ficha_herramienta",
            "codigo_herramienta": "lijadora",
            "tags_regionales": ["lija electrica", "pulidora de madera"],
        },
    },
    # Casi-duplicado 2: mismo concepto que DOC-003 (hidrolavadora), otra jerga, otro id.
    {
        "id": "DOC-018",
        "descripcion_semantica": "Lavadora a presion Karcher para sacar la mugre del frente de la casa, "
        "el patio y las rejas, con manguera larga y boquilla regulable.",
        "metadatos": {
            "categoria": "limpieza",
            "activo": True,
            "tipo_documento": "ficha_herramienta",
            "codigo_herramienta": "hidrolavadora",
            "tags_regionales": ["hidrolavadora a presion", "lavado de frentes"],
        },
    },
    # Colision de ID: dos registros distintos que alguien numero igual a mano.
    {
        "id": "DOC-019",
        "descripcion_semantica": "Hojas de sierra circular adicionales para metal fino, se cotizan "
        "aparte del alquiler base de la sierra.",
        "metadatos": {
            "categoria": "electrico",
            "activo": True,
            "tipo_documento": "politica",
            "tags_regionales": ["hojas de sierra", "repuesto de sierra"],
        },
    },
    {
        "id": "DOC-019",
        "descripcion_semantica": "Manguera adicional de 5 metros para la hidrolavadora, para llegar a "
        "zonas mas alejadas de la toma de agua.",
        "metadatos": {
            "categoria": "limpieza",
            "activo": True,
            "tipo_documento": "politica",
            "tags_regionales": ["manguera extra", "extension hidrolavadora"],
        },
    },
    # Inconsistencia estructural 1: clave mal nombrada ("descripcion" en vez de "descripcion_semantica").
    {
        "id": "DOC-020",
        "descripcion": "Politica de reprogramacion de turno: el cliente puede cambiar la fecha de "
        "retiro de una reserva ya confirmada hasta dos veces, sin costo, avisando con al menos "
        "12 horas de anticipacion.",
        "metadatos": {
            "categoria": "politica",
            "activo": True,
            "tipo_documento": "politica",
            "tags_regionales": ["cambiar la fecha", "reprogramar", "mover el turno"],
        },
    },
    # Inconsistencia estructural 2: booleano cargado como string ("si" en vez de true).
    {
        "id": "DOC-021",
        "descripcion_semantica": "Politica de devolucion de la hidrolavadora: debe entregarse escurrida "
        "de agua y sin residuos de detergente; si vuelve sucia por dentro se cobra un cargo de "
        "limpieza fijo.",
        "metadatos": {
            "categoria": "politica",
            "activo": "si",
            "tipo_documento": "politica",
            "tags_regionales": ["devolver limpia", "cargo de limpieza"],
        },
    },
]


# --------------------------------------------------------------------------
# Paso 1: normalizar claves y tipos
# --------------------------------------------------------------------------


def normalizar_claves_y_tipos(registros: list[dict]) -> list[dict]:
    """Un SELECT sobre este lote ya rompe antes de comparar nada: la columna de texto ni
    siquiera se llama igual en todos los registros, y un campo booleano viene como string."""
    valores_verdaderos = {"si", "sí", "true", "verdadero", "1"}
    valores_falsos = {"no", "false", "falso", "0"}
    normalizados = []

    for registro in registros:
        registro = dict(registro)

        if "descripcion_semantica" not in registro and "descripcion" in registro:
            print(f"  [normalizar] {registro['id']}: clave 'descripcion' -> 'descripcion_semantica'")
            registro["descripcion_semantica"] = registro.pop("descripcion")

        metadatos = dict(registro["metadatos"])
        activo = metadatos.get("activo")
        if isinstance(activo, str):
            clave = activo.strip().lower()
            valor = clave in valores_verdaderos
            if clave not in valores_verdaderos | valores_falsos:
                print(f"  [normalizar] {registro['id']}: activo='{activo}' no reconocido, se asume False")
                valor = False
            print(f"  [normalizar] {registro['id']}: activo '{activo}' (str) -> {valor} (bool)")
            metadatos["activo"] = valor
        registro["metadatos"] = metadatos
        normalizados.append(registro)

    return normalizados


# --------------------------------------------------------------------------
# Paso 2: resolver colision de IDs
# --------------------------------------------------------------------------


def resolver_colision_ids(registros: list[dict], ids_existentes: set[str]) -> list[dict]:
    """Si dos registros del lote comparten id, o un id nuevo ya existe en la base canonica,
    se le asigna el proximo id libre de un rango reservado (DOC-9xx) -- nunca se pisa
    silenciosamente un documento existente ni otro registro del mismo lote."""
    usados = set(ids_existentes)
    vistos_en_lote: set[str] = set()
    resueltos = []

    def proximo_id_libre() -> str:
        n = 900  # rango reservado para reasignaciones, no interfiere con IDs "naturales"
        while f"DOC-{n}" in usados:
            n += 1
        return f"DOC-{n}"

    for registro in registros:
        registro = dict(registro)
        id_original = registro["id"]
        if id_original in vistos_en_lote or id_original in usados:
            nuevo_id = proximo_id_libre()
            print(f"  [colision] id '{id_original}' repetido/ya usado -> reasignado a '{nuevo_id}'")
            registro["id"] = nuevo_id
        usados.add(registro["id"])
        vistos_en_lote.add(registro["id"])
        resueltos.append(registro)

    return resueltos


# --------------------------------------------------------------------------
# Paso 3: purga semantica (embeddings + distancia coseno contra la base canonica)
# --------------------------------------------------------------------------


def _crear_cliente():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("ERROR: falta GEMINI_API_KEY en .env")
    from google import genai

    return genai.Client(api_key=api_key)


def _embed(cliente, textos: list[str]) -> np.ndarray:
    modelo = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    respuesta = cliente.models.embed_content(model=modelo, contents=textos)
    vectores = np.array([e.values for e in respuesta.embeddings], dtype="float32")
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    return vectores / normas


def purgar_casi_duplicados(cliente, registros: list[dict], base_canonica: list[dict]) -> list[dict]:
    """Vectoriza cada registro nuevo y lo compara contra TODA la base canonica. Si la
    distancia coseno al vecino mas cercano cae bajo el umbral de duplicado, se descarta:
    ya hay un documento equivalente, aunque id y texto sean distintos. Un SELECT DISTINCT
    jamas detecta esto porque compara texto exacto, no significado."""
    textos_nuevos = [r["descripcion_semantica"] for r in registros]
    textos_base = [d["descripcion_semantica"] for d in base_canonica]

    vectores_nuevos = _embed(cliente, textos_nuevos)
    vectores_base = _embed(cliente, textos_base)

    conservados = []
    for registro, vector in zip(registros, vectores_nuevos):
        distancias = 1.0 - (vectores_base @ vector)
        idx = int(np.argmin(distancias))
        distancia_minima = float(distancias[idx])
        doc_parecido = base_canonica[idx]
        etiqueta = doc_parecido["metadatos"].get("codigo_herramienta") or doc_parecido["metadatos"].get(
            "tipo_documento"
        )

        if distancia_minima < UMBRAL_DUPLICADO:
            print(
                f"  [purga] {registro['id']} PURGADO: distancia {distancia_minima:.4f} a "
                f"{doc_parecido['id']} ({etiqueta}) -- por debajo del umbral {UMBRAL_DUPLICADO}. "
                f"Ni el id ni el texto coinciden con {doc_parecido['id']}: un SELECT DISTINCT los "
                f"habria tratado como dos filas distintas."
            )
        else:
            print(
                f"  [purga] {registro['id']} CONSERVADO: distancia minima {distancia_minima:.4f} a "
                f"{doc_parecido['id']} ({etiqueta}), por encima del umbral -- contenido nuevo real."
            )
            conservados.append(registro)

    return conservados


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------


def main() -> None:
    with open(BASE_CONOCIMIENTO, encoding="utf-8") as fh:
        base_canonica = json.load(fh)
    ids_existentes = {d["id"] for d in base_canonica}

    print("=" * 78)
    print(f"Lote crudo: {len(DATOS_CRUDOS)} registros a integrar a una base de {len(base_canonica)} documentos")
    print("=" * 78)

    print("\n--- Paso 1: normalizar claves y tipos ---")
    normalizados = normalizar_claves_y_tipos(DATOS_CRUDOS)

    print("\n--- Paso 2: resolver colision de IDs ---")
    resueltos = resolver_colision_ids(normalizados, ids_existentes)

    print("\n--- Paso 3: purga semantica contra la base canonica ---")
    cliente = _crear_cliente()
    conservados = purgar_casi_duplicados(cliente, resueltos, base_canonica)

    print("\n" + "=" * 78)
    print(f"Resultado: {len(conservados)}/{len(resueltos)} registros son contenido nuevo real.")
    print(f"Purgados: {len(resueltos) - len(conservados)} casi-duplicados de documentos ya existentes.")
    for r in conservados:
        print(f"  -> listo para sumarse a la base: {r['id']}")


if __name__ == "__main__":
    main()
