"""
varianza_jueces.py - Varianza de los dos jueces LLM entre corridas repetidas (correccion de B.4).

Feedback: "el costo del reranking esta bien medido, pero no se mide la varianza del juez entre
corridas repetidas de la misma pregunta". Hay dos jueces LLM en esta entrega y se miden los dos:

1. Juez de relevancia del reranker (B.3), gemini-3.5-flash-lite.
   Para cada pregunta se recuperan los candidatos UNA vez y se le pide al juez N veces el puntaje
   sobre exactamente la misma entrada: la unica fuente de variacion es el juez (Gemini 3.5 ignora
   temperature=0). Se mide media / desvio / rango del puntaje de cada chunk, cuantas veces cada
   chunk supera el corte (>= 6) y si el conjunto final seleccionado cambia entre repeticiones.

2. Juez de RAGAS (C.3), el mismo modelo que la tabla comparativa (RAGAS_LLM_MODEL).
   Se re-evaluan las MISMAS respuestas del avanzado (sin regenerarlas) R veces mas; la corrida de
   referencia (metricas_avanzado.json) es la repeticion 1. Se reporta el desvio de cada metrica
   agregada y por pregunta, y se compara con los deltas de C.3 para separar mejora de ruido.

Uso (desde la raiz del repo):
    py entrega_3/varianza_jueces.py --reranker 5     # 3 preguntas x 5 repeticiones del juez
    py entrega_3/varianza_jueces.py --ragas 2        # 2 re-evaluaciones RAGAS del avanzado
    py entrega_3/varianza_jueces.py                  # solo rehace resultados_varianza.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

DIR_ENTREGA = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_ENTREGA))

import evaluacion_ragas as ev  # noqa: E402
import rag_pipeline as rp  # noqa: E402

DIR_VARIANZA = ev.DIR_RESULTADOS / "varianza"
REPORTE_MD = DIR_ENTREGA / "resultados_varianza.md"

# Una pregunta de cada situacion que el juez de relevancia tiene que resolver.
PREGUNTAS_RERANKER = [
    ("B.1", rp.CASOS_FALLA[0]["pregunta"], "multi-parte: descartar la ficha ruidosa y quedarse con 4 políticas"),
    ("C6", "Alquilo la hidrolavadora para el finde: ¿qué necesito tener en casa para usarla, qué hago si deja "
     "de andar, y cómo hago para devolverla si el domingo está cerrado?", "multi-parte con ficha necesaria"),
    ("E2", "¿Alquilan motosierras para podar árboles?", "escape: ningún chunk debería pasar el corte"),
]


# --------------------------------------------------------------------------
# 1. Juez de relevancia (reranker)
# --------------------------------------------------------------------------


def varianza_reranker(repeticiones: int) -> dict:
    vectorstore = rp.obtener_vectorstore(rp.NOMBRE_COLECCION_CHUNKS)
    llm = rp.obtener_llm()
    juez = rp._reranker(llm)
    recuperar = rp._retriever_candidatos(vectorstore)
    salida = {}
    for clave, pregunta, que_prueba in PREGUNTAS_RERANKER:
        candidatos = recuperar.invoke(pregunta)
        ids = rp._ids(candidatos)
        puntajes = {i: [] for i in ids}
        seleccionados = []
        for n in range(repeticiones):
            # Copias frescas: el reranker escribe el puntaje en metadata y no queremos arrastrarlo.
            copia = [type(d)(page_content=d.page_content, metadata=dict(d.metadata)) for d in candidatos]
            elegidos = juez.invoke({"pregunta": pregunta, "candidatos": copia})
            for d in copia:
                puntajes[rp._ids([d])[0]].append(d.metadata["puntaje_juez"])
            seleccionados.append(sorted(rp._ids(elegidos)))
            print(f"  [{clave}] repeticion {n + 1}: seleccionados={seleccionados[-1]}")
        salida[clave] = {
            "pregunta": pregunta,
            "que_prueba": que_prueba,
            "candidatos": ids,
            "distancias": [d.metadata["distancia"] for d in candidatos],
            "puntajes": puntajes,
            "seleccionados": seleccionados,
        }
    DIR_VARIANZA.mkdir(parents=True, exist_ok=True)
    (DIR_VARIANZA / "reranker.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    return salida


# --------------------------------------------------------------------------
# 2. Juez de RAGAS
# --------------------------------------------------------------------------


def varianza_ragas(extra: int) -> None:
    for n in range(2, 2 + extra):
        print(f"\nRe-evaluacion RAGAS del avanzado, repeticion {n}")
        filas = ev.agregar_metricas_id(ev.evaluar("avanzado", sufijo=f"_rep{n}"))
        destino = DIR_VARIANZA / f"metricas_avanzado_rep{n}.json"
        DIR_VARIANZA.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
        (ev.DIR_RESULTADOS / f"metricas_avanzado_rep{n}.json").unlink()  # queda solo la copia en varianza/


def _repeticiones_ragas() -> list[list[dict]]:
    reps = [json.loads((ev.DIR_RESULTADOS / "metricas_avanzado.json").read_text(encoding="utf-8"))]
    for ruta in sorted(DIR_VARIANZA.glob("metricas_avanzado_rep*.json")):
        reps.append(json.loads(ruta.read_text(encoding="utf-8")))
    return reps


# --------------------------------------------------------------------------
# Reporte
# --------------------------------------------------------------------------


def _std(valores: list[float]) -> float:
    return statistics.pstdev(valores) if len(valores) > 1 else 0.0


def _entre_jueces() -> list[str]:
    """Mismas respuestas (las 10 preguntas originales del golden), dos jueces distintos:
    corrida 1 (gemini-3.5-flash-lite) vs. corrida de referencia (gemini-3.1-flash-lite)."""
    dir_c1 = ev.DIR_RESULTADOS / "corrida_1_10_preguntas"
    if not dir_c1.exists():
        return []
    lineas = [
        "## 3. Variación entre jueces distintos (la que sí pesa)",
        "",
        "Las mismas respuestas de las 10 preguntas originales, evaluadas por `gemini-3.5-flash-lite` (corrida 1) "
        "y por `gemini-3.1-flash-lite` (corrida de referencia de C.3).",
        "",
        "| Pipeline | Métrica | Juez 3.5-flash-lite | Juez 3.1-flash-lite | Diferencia | Preguntas con diferencia > 0.2 |",
        "|---|---|---|---|---|---|",
    ]
    for nombre in ("basico", "avanzado"):
        c1 = {f["id"]: f for f in json.loads((dir_c1 / f"metricas_{nombre}.json").read_text(encoding="utf-8"))}
        c2 = {f["id"]: f for f in json.loads((ev.DIR_RESULTADOS / f"metricas_{nombre}.json").read_text(encoding="utf-8"))}
        ids = [i for i in c1 if i in c2]
        for m in ev.METRICAS:
            pares = [(c1[i][m], c2[i][m]) for i in ids if c1[i].get(m) is not None and c2[i].get(m) is not None]
            a = statistics.mean(p[0] for p in pares)
            b = statistics.mean(p[1] for p in pares)
            distintas = [i for i in ids if c1[i].get(m) is not None and c2[i].get(m) is not None
                         and abs(c1[i][m] - c2[i][m]) > 0.2]
            lineas.append(
                f"| {nombre} | {ev.ETIQUETAS[m]} | {a:.3f} | {b:.3f} | {b - a:+.3f} | "
                f"{len(distintas)}/{len(pares)} ({', '.join(distintas) or '—'}) |"
            )
    return lineas + [""]


def escribir_reporte() -> None:
    lineas = [
        "# Varianza de los jueces LLM (corrección de B.4)",
        "",
        f"**Fecha del reporte:** {date.today().isoformat()}",
        "",
    ]

    ruta_rr = DIR_VARIANZA / "reranker.json"
    if ruta_rr.exists():
        datos = json.loads(ruta_rr.read_text(encoding="utf-8"))
        n_rep = len(next(iter(datos.values()))["seleccionados"])
        lineas += [
            "## 1. Juez de relevancia del reranker",
            "",
            f"Modelo `{rp.os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')}`, {n_rep} repeticiones sobre los mismos 8 "
            f"candidatos (recuperados una sola vez). Corte de selección: puntaje ≥ {rp.PUNTAJE_MINIMO}.",
            "",
        ]
        for clave, d in datos.items():
            conjuntos = [tuple(s) for s in d["seleccionados"]]
            moda = max(set(conjuntos), key=conjuntos.count)
            lineas += [
                f"### {clave} — {d['que_prueba']}",
                "",
                f"> {d['pregunta']}",
                "",
                f"**Conjunto seleccionado idéntico en {conjuntos.count(moda)}/{n_rep} repeticiones** "
                f"(el más frecuente: {', '.join(moda) or 'vacío → frase de escape'}).",
                "",
                "| Chunk | Distancia | Puntajes | Media | Desvío | Rango | Veces ≥ corte |",
                "|---|---|---|---|---|---|---|",
            ]
            for chunk, dist in zip(d["candidatos"], d["distancias"]):
                p = d["puntajes"][chunk]
                lineas.append(
                    f"| {chunk} | {dist} | {', '.join(map(str, p))} | {statistics.mean(p):.1f} | {_std(p):.2f} | "
                    f"{max(p) - min(p)} | {sum(x >= rp.PUNTAJE_MINIMO for x in p)}/{len(p)} |"
                )
            lineas.append("")

    reps = _repeticiones_ragas()
    if len(reps) > 1:
        juez = ev.os.getenv("RAGAS_LLM_MODEL") or "gemini-3.1-flash-lite"
        lineas += [
            "## 2. Juez de RAGAS",
            "",
            f"Juez `{juez}` (el mismo de la tabla C.3), **las mismas 13 respuestas del avanzado** evaluadas "
            f"{len(reps)} veces. La repetición 1 es la corrida entregada (`metricas_avanzado.json`).",
            "",
            "| Métrica | " + " | ".join(f"Rep. {i + 1}" for i in range(len(reps)))
            + " | Media | Desvío entre corridas | Desvío medio por pregunta | Rango máx. por pregunta |",
            "|---|" + "---|" * (len(reps) + 4),
        ]
        for m in ev.METRICAS:
            agregados = [ev._promedio(r, m)[0] for r in reps]
            por_pregunta = []
            rangos = []
            for i in range(len(reps[0])):
                vals = [r[i][m] for r in reps if r[i].get(m) is not None]
                if len(vals) > 1:
                    por_pregunta.append(_std(vals))
                    rangos.append(max(vals) - min(vals))
            lineas.append(
                f"| {ev.ETIQUETAS[m]} | " + " | ".join(ev._fmt(a) for a in agregados)
                + f" | {statistics.mean(agregados):.3f} | {_std(agregados):.3f} | "
                f"{statistics.mean(por_pregunta):.3f} | {max(rangos):.3f} |"
            )
        lineas += [
            "",
            "Preguntas cuyo puntaje cambia entre repeticiones (rango > 0.2):",
            "",
        ]
        hubo_cambios = False
        for i, fila in enumerate(reps[0]):
            cambios = []
            for m in ev.METRICAS:
                vals = [r[i][m] for r in reps if r[i].get(m) is not None]
                if len(vals) > 1 and max(vals) - min(vals) > 0.2:
                    cambios.append(f"{ev.ETIQUETAS[m]} {' / '.join(ev._fmt(v) for v in vals)}")
            if cambios:
                hubo_cambios = True
                lineas.append(f"- **{fila['id']}**: " + "; ".join(cambios))
        if not hubo_cambios:
            lineas.append("- Ninguna: con el mismo juez, cada pregunta recibe el mismo puntaje en todas las repeticiones.")
        lineas.append("")

    lineas += _entre_jueces()

    REPORTE_MD.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\nReporte escrito en {REPORTE_MD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Varianza de los jueces LLM")
    parser.add_argument("--reranker", type=int, metavar="N", help="Repeticiones del juez de relevancia")
    parser.add_argument("--ragas", type=int, metavar="R", help="Re-evaluaciones RAGAS extra del avanzado")
    args = parser.parse_args()
    if args.reranker:
        varianza_reranker(args.reranker)
    if args.ragas:
        varianza_ragas(args.ragas)
    escribir_reporte()


if __name__ == "__main__":
    main()
