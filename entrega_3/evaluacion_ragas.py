"""
evaluacion_ragas.py - Evaluacion con RAGAS (Entrega 3, Parte C).

C.1 El golden dataset vive en golden_dataset.json, separado del codigo porque se reusa en las
    Entregas 4 y 5: 13 preguntas (3 simples, 6 complejas, 2 de escape, 2 informales). Las 10
    originales no se usaron para desarrollar ni ajustar el pipeline; las complejas C4-C6
    (origen "agregada_post_corrida_1") se sumaron despues de la primera corrida porque ninguna
    pregunta original ejercitaba consultas multi-parte (ver informe.md, C.1).
C.2 Baseline: RAG basico con Faithfulness, Answer Relevancy, Context Precision y Context Recall.
C.3 Comparativa basico vs. avanzado (y opcionalmente la ablacion "solo chunking").

Dos pasos separados, para no volver a pagar la generacion si solo se re-evalua:
    1. generar: corre cada pipeline sobre el dataset y guarda respuestas + contextos en JSON.
    2. evaluar: corre RAGAS sobre esos JSON y escribe resultados_ragas.md.

Uso (desde la raiz del repo):
    py entrega_3/evaluacion_ragas.py                                  # basico + avanzado, generar y evaluar
    py entrega_3/evaluacion_ragas.py --pipelines basico avanzado solo_chunks
    py entrega_3/evaluacion_ragas.py --solo-evaluar                   # reusa las respuestas ya guardadas
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import date
from pathlib import Path

DIR_ENTREGA = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_ENTREGA))

import rag_pipeline as rp  # noqa: E402  (carga el .env y LangSmith antes que LangChain)

GOLDEN = DIR_ENTREGA / "golden_dataset.json"
DIR_RESULTADOS = DIR_ENTREGA / "resultados_ragas"
REPORTE_MD = DIR_ENTREGA / "resultados_ragas.md"

CONSTRUCTORES = {
    "basico": rp.construir_rag_basico,
    "solo_chunks": rp.construir_rag_solo_chunks,
    "avanzado": rp.construir_rag_avanzado,
}
NOMBRES = {
    "basico": "RAG básico (docs enteros, k=3, umbral)",
    "solo_chunks": "Solo chunking (500/100, k=3, sin juez)",
    "avanzado": "RAG avanzado (chunks 500/100, k=8 + juez LLM)",
}
METRICAS = ["faithfulness", "answer_relevancy", "llm_context_precision_with_reference", "context_recall"]
# Versiones deterministicas (sin LLM) de las metricas de contexto: comparan los ids recuperados
# contra docs_esperados del golden dataset. Sirven de control del juez LLM (ver informe, C.3).
METRICAS_ID = ["id_context_precision", "id_context_recall"]
ETIQUETAS = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer Relevancy",
    "llm_context_precision_with_reference": "Context Precision",
    "context_recall": "Context Recall",
    "id_context_precision": "Context Precision por IDs (sin LLM)",
    "id_context_recall": "Context Recall por IDs (sin LLM)",
}


def cargar_golden() -> list[dict]:
    with open(GOLDEN, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Paso 1 - Generar respuestas
# --------------------------------------------------------------------------


def generar(nombre: str, golden: list[dict], incremental: bool = False) -> Path:
    """incremental=True: solo genera las preguntas que todavia no estan en el JSON guardado
    (las ya respondidas no se regeneran, para no cambiar respuestas ya evaluadas)."""
    rag = CONSTRUCTORES[nombre]()
    ruta = DIR_RESULTADOS / f"respuestas_{nombre}.json"
    previas = {}
    if incremental and ruta.exists():
        previas = {f["id"]: f for f in json.loads(ruta.read_text(encoding="utf-8"))}
    filas = []
    for item in golden:
        if item["id"] in previas:
            filas.append({**previas[item["id"]], **item})
            continue
        print(f"  [{nombre}] {item['id']}: {item['pregunta']}")
        inicio = time.perf_counter()
        salida = rag.invoke(item["pregunta"], config={"tags": ["entrega_3", "ragas", nombre]})
        filas.append(
            {
                **item,
                "respuesta": salida["respuesta"],
                "contextos": [d.page_content for d in salida["contexto"]],
                "ids_contexto": rp._ids(salida["contexto"]),
                "segundos": round(time.perf_counter() - inicio, 2),
            }
        )
    DIR_RESULTADOS.mkdir(exist_ok=True)
    ruta.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


# --------------------------------------------------------------------------
# Paso 2 - Evaluar con RAGAS
# --------------------------------------------------------------------------


def _evaluador():
    from langchain_google_genai import ChatGoogleGenerativeAI
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    # El juez de RAGAS puede ser otro modelo (RAGAS_LLM_MODEL); por defecto, el mismo del pipeline.
    modelo = os.getenv("RAGAS_LLM_MODEL") or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    llm = ChatGoogleGenerativeAI(model=modelo, temperature=0, max_retries=8)
    # bypass_n: Answer Relevancy pide n=3 preguntas generadas en una sola llamada (n candidatos) y
    # Gemini 3.5 responde 400 "Multiple candidates is not enabled". Con bypass_n RAGAS hace las 3
    # llamadas por separado: mismo resultado, sin NaN.
    return LangchainLLMWrapper(llm, bypass_n=True), LangchainEmbeddingsWrapper(rp.EmbeddingsEntrega2()), modelo


def evaluar(nombre: str) -> list[dict]:
    from ragas import EvaluationDataset, RunConfig, evaluate
    from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall, ResponseRelevancy

    filas = json.loads((DIR_RESULTADOS / f"respuestas_{nombre}.json").read_text(encoding="utf-8"))
    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": f["pregunta"],
                "response": f["respuesta"],
                "retrieved_contexts": f["contextos"],
                "reference": f["ground_truth"],
            }
            for f in filas
        ]
    )
    llm, embeddings, _ = _evaluador()
    resultado = evaluate(
        dataset,
        metrics=[Faithfulness(), ResponseRelevancy(), LLMContextPrecisionWithReference(), LLMContextRecall()],
        llm=llm,
        embeddings=embeddings,
        # Pocos workers: el free tier de Gemini corta rafagas con 429.
        run_config=RunConfig(max_workers=2, timeout=240, max_retries=10, max_wait=90),
        raise_exceptions=False,
    )
    df = resultado.to_pandas()
    for fila, (_, r) in zip(filas, df.iterrows()):
        for m in METRICAS:
            valor = r.get(m)
            fila[m] = None if valor is None or (isinstance(valor, float) and math.isnan(valor)) else round(float(valor), 4)
    ruta = DIR_RESULTADOS / f"metricas_{nombre}.json"
    ruta.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    return filas


def agregar_metricas_id(filas: list[dict]) -> list[dict]:
    """IDBasedContextPrecision / IDBasedContextRecall de RAGAS. Las preguntas de escape no tienen
    documentos esperados: ahi las metricas no estan definidas y quedan en None."""
    import asyncio

    from ragas import SingleTurnSample
    from ragas.metrics import IDBasedContextPrecision, IDBasedContextRecall

    precision, recall = IDBasedContextPrecision(), IDBasedContextRecall()
    for f in filas:
        if not f["docs_esperados"]:
            f["id_context_precision"] = f["id_context_recall"] = None
            continue
        muestra = SingleTurnSample(
            retrieved_context_ids=[i.split("#")[0] for i in f["ids_contexto"]],
            reference_context_ids=f["docs_esperados"],
        )
        f["id_context_precision"] = round(asyncio.run(precision.single_turn_ascore(muestra)), 4)
        f["id_context_recall"] = round(asyncio.run(recall.single_turn_ascore(muestra)), 4)
    return filas


# --------------------------------------------------------------------------
# Reporte
# --------------------------------------------------------------------------


def _promedio(filas: list[dict], metrica: str, filtro=lambda f: True) -> tuple[float | None, int]:
    valores = [f[metrica] for f in filas if filtro(f) and f.get(metrica) is not None]
    return (sum(valores) / len(valores) if valores else None, len(valores))


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}"


def _hit_rate(filas: list[dict]) -> float:
    """Metrica determinista (sin LLM): fraccion de documentos esperados que llegaron al contexto."""
    esperados = encontrados = 0
    for f in filas:
        ids = {i.split("#")[0] for i in f["ids_contexto"]}
        esperados += len(f["docs_esperados"])
        encontrados += sum(d in ids for d in f["docs_esperados"])
    return encontrados / esperados if esperados else 0.0


def escribir_reporte(resultados: dict[str, list[dict]], modelo_juez: str) -> None:
    nombres = list(resultados)
    base = "basico" if "basico" in resultados else nombres[0]
    lineas = [
        "# Resultados RAGAS (Entrega 3, Parte C)",
        "",
        f"**Fecha de corrida:** {date.today().isoformat()}  ",
        f"**Dataset:** `golden_dataset.json`, {len(resultados[base])} preguntas: "
        + ", ".join(f"{sum(f['tipo'] == t for f in resultados[base])} {t}" for t in ("simple", "compleja", "escape", "informal"))
        + f" ({sum(f.get('origen') != 'original' for f in resultados[base])} complejas agregadas después de la 1.ª corrida, "
        "ver informe C.1)  ",
        f"**LLM juez de RAGAS:** `{modelo_juez}` · **Embeddings:** `gemini-embedding-001`  ",
        "",
        "## C.2 / C.3 — Comparativa (promedio sobre las preguntas con métrica válida)",
        "",
        "| Métrica | " + " | ".join(NOMBRES[n] for n in nombres) + " | Delta (avanzado − básico) |",
        "|---|" + "---|" * len(nombres) + "---|",
    ]
    for m in METRICAS + METRICAS_ID:
        valores = {n: _promedio(resultados[n], m) for n in nombres}
        celdas = [f"{_fmt(v)} (n={k})" if k != len(resultados[n]) else _fmt(v) for n, (v, k) in valores.items()]
        delta = "—"
        if "avanzado" in valores and "basico" in valores and None not in (valores["avanzado"][0], valores["basico"][0]):
            d = valores["avanzado"][0] - valores["basico"][0]
            delta = f"**{d:+.3f}**"
        lineas.append(f"| {ETIQUETAS[m]} | " + " | ".join(celdas) + f" | {delta} |")
    hits = {n: _hit_rate(resultados[n]) for n in nombres}
    delta_hit = f"{hits['avanzado'] - hits['basico']:+.3f}" if {"avanzado", "basico"} <= hits.keys() else "—"
    lineas.append(
        "| Hit rate de documentos esperados (sin LLM) | " + " | ".join(f"{hits[n]:.3f}" for n in nombres) + f" | {delta_hit} |"
    )
    lineas += ["", "Las dos métricas \"por IDs\" y el hit rate no usan LLM: se calculan sobre las preguntas con "
               "`docs_esperados` (todas menos las 2 de escape)."]

    lineas += ["", "## Por tipo de pregunta", ""]
    for tipo in ["simple", "compleja", "escape", "informal"]:
        lineas += [f"**{tipo}**", "", "| Métrica | " + " | ".join(nombres) + " |", "|---|" + "---|" * len(nombres)]
        for m in METRICAS:
            lineas.append(
                f"| {ETIQUETAS[m]} | "
                + " | ".join(_fmt(_promedio(resultados[n], m, lambda f: f["tipo"] == tipo)[0]) for n in nombres)
                + " |"
            )
        lineas.append("")

    lineas += ["## Sin las preguntas de escape", "",
               "Las de escape tienen una respuesta correcta que es, a propósito, 'no sé': RAGAS la castiga en "
               "Answer Relevancy (respuesta evasiva) y Context Recall/Precision no tienen sentido sin contexto "
               "esperado. Esta vista muestra solo las preguntas con respuesta en la base.", "",
               "| Métrica | " + " | ".join(nombres) + " |", "|---|" + "---|" * len(nombres)]
    for m in METRICAS:
        lineas.append(
            f"| {ETIQUETAS[m]} | "
            + " | ".join(_fmt(_promedio(resultados[n], m, lambda f: f["tipo"] != "escape")[0]) for n in nombres)
            + " |"
        )

    vistas = [
        ("Solo las 10 preguntas originales", lambda f: f.get("origen", "original") == "original"),
        ("Solo las 3 complejas agregadas", lambda f: f.get("origen", "original") != "original"),
    ]
    for titulo, filtro in vistas:
        lineas += ["", f"## {titulo}", "", "| Métrica | " + " | ".join(nombres) + " |", "|---|" + "---|" * len(nombres)]
        for m in METRICAS:
            lineas.append(
                f"| {ETIQUETAS[m]} | " + " | ".join(_fmt(_promedio(resultados[n], m, filtro)[0]) for n in nombres) + " |"
            )

    lineas += ["", "## Detalle por pregunta", ""]
    for n in nombres:
        lineas += [f"### {NOMBRES[n]}", "",
                   "| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |",
                   "|---|---|---|---|---|---|---|---|"]
        for f in resultados[n]:
            resp = " ".join(f["respuesta"].split()).replace("|", "\\|")
            lineas.append(
                f"| {f['id']} | {f['tipo']} | {', '.join(f['ids_contexto']) or '—'} | "
                + " | ".join(_fmt(f.get(m)) for m in METRICAS)
                + f" | {resp} |"
            )
        lineas.append("")

    REPORTE_MD.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\nReporte escrito en {REPORTE_MD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluacion RAGAS - AlquiHerramientas")
    parser.add_argument("--pipelines", nargs="+", default=["basico", "avanzado"], choices=list(CONSTRUCTORES))
    parser.add_argument("--solo-evaluar", action="store_true", help="No regenera respuestas, reusa los JSON")
    parser.add_argument("--solo-generar", action="store_true", help="Solo genera respuestas, sin RAGAS")
    parser.add_argument("--incremental", action="store_true", help="Solo genera las preguntas nuevas del dataset")
    parser.add_argument("--solo-reporte", action="store_true",
                        help="Rehace el reporte desde metricas_*.json, sin llamar al LLM")
    args = parser.parse_args()

    golden = cargar_golden()
    conteo = {t: sum(g["tipo"] == t for g in golden) for t in ("simple", "compleja", "escape", "informal")}
    print(f"Golden dataset: {len(golden)} preguntas {conteo}")

    if not (args.solo_evaluar or args.solo_reporte):
        for nombre in args.pipelines:
            print(f"\nGenerando respuestas: {NOMBRES[nombre]}")
            print(f"  -> {generar(nombre, golden, incremental=args.incremental)}")
    if args.solo_generar:
        return

    if args.solo_reporte:
        resultados = {}
        for nombre in args.pipelines:
            filas = json.loads((DIR_RESULTADOS / f"metricas_{nombre}.json").read_text(encoding="utf-8"))
            golden_por_id = {g["id"]: g for g in golden}
            resultados[nombre] = agregar_metricas_id([{**f, **golden_por_id[f["id"]]} for f in filas])
            (DIR_RESULTADOS / f"metricas_{nombre}.json").write_text(
                json.dumps(resultados[nombre], ensure_ascii=False, indent=2), encoding="utf-8")
        escribir_reporte(resultados, os.getenv("RAGAS_LLM_MODEL") or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))
        return

    resultados = {}
    for nombre in args.pipelines:
        print(f"\nEvaluando con RAGAS: {NOMBRES[nombre]}")
        resultados[nombre] = agregar_metricas_id(evaluar(nombre))
        (DIR_RESULTADOS / f"metricas_{nombre}.json").write_text(
            json.dumps(resultados[nombre], ensure_ascii=False, indent=2), encoding="utf-8")
        for m in METRICAS:
            v, k = _promedio(resultados[nombre], m)
            print(f"  {ETIQUETAS[m]:<18} {_fmt(v)}  (n={k})")
    escribir_reporte(resultados, _evaluador()[2])


if __name__ == "__main__":
    main()
