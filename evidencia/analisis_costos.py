"""
analisis_costos.py - Analisis de costos y latencia desde las trazas de LangSmith (TP Final, Parte C).

Lee de LangSmith (con la LANGSMITH_API_KEY del .env) las corridas raiz "agente_alquiherramientas"
de un dia y, para cada una, sus llamadas al LLM: separa las del agente (decidir herramientas y
redactar) de las del juez de relevancia que corre dentro de buscar_informacion. El costo es el
total_cost que calcula LangSmith con su tabla de precios del modelo.

    python evidencia/analisis_costos.py                 # trazas de hoy
    python evidencia/analisis_costos.py --desde 2026-11-16
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")

SALIDA_MD = Path(__file__).resolve().parent / "analisis_costos.md"
CONSULTAS_POR_DIA = 3000  # mismo volumen de referencia que la Entrega 1 (A.4) y la Entrega 2 (A.1)


def _p(valores: list[float], q: float) -> float:
    ordenados = sorted(valores)
    return ordenados[max(0, min(len(ordenados) - 1, int(round(q / 100 * len(ordenados) + 0.5)) - 1))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", default=date.today().isoformat())
    args = parser.parse_args()
    if not os.getenv("LANGSMITH_API_KEY"):
        raise SystemExit("Falta LANGSMITH_API_KEY en .env")

    from langsmith import Client

    cliente = Client()
    proyecto = os.getenv("LANGSMITH_PROJECT", "default")
    desde = datetime.fromisoformat(args.desde).replace(tzinfo=timezone.utc)
    raices = [
        r for r in cliente.list_runs(project_name=proyecto, is_root=True, start_time=desde,
                                     filter='eq(name, "agente_alquiherramientas")')
        # prompt_tokens > 0 descarta corridas con modelos falsos (tests de versiones anteriores)
        if r.end_time and r.error is None and (r.prompt_tokens or 0) > 0
    ]
    if not raices:
        raise SystemExit(f"No hay trazas de agente_alquiherramientas en {proyecto} desde {args.desde}")

    filas = []
    for raiz in sorted(raices, key=lambda r: r.start_time):
        hijos = list(cliente.list_runs(project_name=proyecto, trace_id=raiz.trace_id))
        # "retriever_conocimiento" desde la organizacion en slices; "retriever_e3" en las trazas anteriores
        retrievers = [h.id.hex for h in hijos if h.name in ("retriever_conocimiento", "retriever_e3")]
        llm = [h for h in hijos if h.run_type == "llm"]
        juez = [h for h in llm if any(rid in (h.dotted_order or "").replace("-", "") for rid in retrievers)]
        agente = [h for h in llm if h not in juez]
        herramientas = [h.name for h in hijos if h.run_type == "tool"]
        filas.append({
            "inicio": raiz.start_time,
            "segundos": (raiz.end_time - raiz.start_time).total_seconds(),
            "tokens_in": raiz.prompt_tokens or 0,
            "tokens_out": raiz.completion_tokens or 0,
            "costo": float(raiz.total_cost or 0),
            "llamadas_agente": len(agente),
            "tokens_agente": sum(h.total_tokens or 0 for h in agente),
            "llamadas_juez": len(juez),
            "tokens_juez": sum(h.total_tokens or 0 for h in juez),
            "herramientas": herramientas,
        })

    n = len(filas)
    segundos = [f["segundos"] for f in filas]
    costos = [f["costo"] for f in filas]
    tokens_tot = [f["tokens_in"] + f["tokens_out"] for f in filas]
    con_rag = [f for f in filas if "buscar_informacion" in f["herramientas"]]
    sin_rag = [f for f in filas if "buscar_informacion" not in f["herramientas"]]
    total_agente = sum(f["tokens_agente"] for f in filas)
    total_juez = sum(f["tokens_juez"] for f in filas)
    costo_medio = statistics.mean(costos)

    def promedio(lista, clave):
        return statistics.mean(x[clave] for x in lista) if lista else 0.0

    lineas = [
        "# Análisis de costos y latencia desde LangSmith (TP Final, Parte C)",
        "",
        f"**Proyecto LangSmith:** `{proyecto}` · **Trazas analizadas:** {n} corridas de `agente_alquiherramientas` "
        f"desde {args.desde} (matriz de validación, demo HTTP y pruebas) · **Fecha del reporte:** {date.today().isoformat()}",
        "",
        "El costo de cada traza es el `total_cost` que calcula LangSmith con su tabla de precios del modelo. "
        "Coincide con la tarifa configurada en `app/shared/config.py` (USD 0.30 / 2.50 por millón de tokens de "
        "entrada / salida), así que `/metricas` y LangSmith dan el mismo número.",
        "",
        "## Resumen por consulta",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Tokens por consulta (promedio / p95) | {statistics.mean(tokens_tot):,.0f} / {_p(tokens_tot, 95):,.0f} |",
        f"| Costo por consulta (promedio / p95) | USD {costo_medio:.5f} / USD {_p(costos, 95):.5f} |",
        f"| Latencia (promedio / p50 / p95) | {statistics.mean(segundos):.1f} s / {_p(segundos, 50):.1f} s / {_p(segundos, 95):.1f} s |",
        f"| Llamadas al LLM por consulta (agente + juez) | {promedio(filas, 'llamadas_agente'):.1f} + {promedio(filas, 'llamadas_juez'):.1f} |",
        "",
        "## Dónde se van los tokens",
        "",
        "| Componente | Tokens | Participación |",
        "|---|---|---|",
        f"| Agente (decidir herramientas + redactar) | {total_agente:,} | {total_agente / (total_agente + total_juez):.0%} |",
        f"| Juez de relevancia (dentro de `buscar_informacion`) | {total_juez:,} | {total_juez / (total_agente + total_juez):.0%} |",
        "",
        "| Tipo de consulta | Consultas | Tokens promedio | Costo promedio | Latencia promedio |",
        "|---|---|---|---|---|",
        f"| Usa el RAG (`buscar_informacion`) | {len(con_rag)} | {promedio(con_rag, 'tokens_in') + promedio(con_rag, 'tokens_out'):,.0f} | "
        f"USD {promedio(con_rag, 'costo'):.5f} | {promedio(con_rag, 'segundos'):.1f} s |",
        f"| Solo SQL o sin herramientas | {len(sin_rag)} | {promedio(sin_rag, 'tokens_in') + promedio(sin_rag, 'tokens_out'):,.0f} | "
        f"USD {promedio(sin_rag, 'costo'):.5f} | {promedio(sin_rag, 'segundos'):.1f} s |",
        "",
        f"## Proyección a {CONSULTAS_POR_DIA:,} consultas por día",
        "",
        "| Período | Costo estimado |",
        "|---|---|",
        f"| Día | USD {costo_medio * CONSULTAS_POR_DIA:,.2f} |",
        f"| Mes (30 días) | USD {costo_medio * CONSULTAS_POR_DIA * 30:,.2f} |",
        f"| Año | USD {costo_medio * CONSULTAS_POR_DIA * 365:,.2f} |",
        "",
        "## Detalle por traza",
        "",
        "| Inicio (UTC) | Herramientas | Llamadas LLM (agente/juez) | Tokens entrada/salida | Costo USD | Latencia |",
        "|---|---|---|---|---|---|",
    ]
    for f in filas:
        lineas.append(
            f"| {f['inicio']:%H:%M:%S} | {', '.join(f['herramientas']) or '—'} | {f['llamadas_agente']}/{f['llamadas_juez']} | "
            f"{f['tokens_in']:,}/{f['tokens_out']:,} | {f['costo']:.5f} | {f['segundos']:.1f} s |"
        )
    SALIDA_MD.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[:32]))
    print(f"\nEscrito en {SALIDA_MD}")


if __name__ == "__main__":
    main()
