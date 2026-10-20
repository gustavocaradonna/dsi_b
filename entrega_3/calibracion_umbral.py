"""
calibracion_umbral.py - Recalibracion del umbral de aceptacion (correccion de la Entrega 2).

Feedback de la catedra sobre B.6 / C.2 de la Entrega 2:
  1. El umbral 0.32 se calibro con las MISMAS 3 consultas que despues lo "aprobaban".
  2. buscar_alquiherramientas() no aplicaba el umbral: solo lo usaba el script de prueba.
  3. Calibrar con mas consultas (positivas y negativas) antes de la Entrega 3.

Que hace este script:
  - Define 40 consultas NUEVAS (ninguna es una Killer Query de la Entrega 2): 24 positivas
    (con el documento que deberia responderlas) y 16 negativas (fuera de catalogo; la mitad
    "cercanas al dominio", que son las dificiles).
  - Las divide en dos mitades disjuntas: CALIBRACION (se elige el umbral) y VALIDACION
    (held-out: se mide el umbral elegido sobre consultas que no participaron de la eleccion).
  - Para cada umbral candidato mide aciertos sobre calibracion y elige el que maximiza el
    balanced accuracy (promedio de recall de positivas y de negativas).
  - Reporta la matriz de confusion del umbral elegido en VALIDACION, y ademas como quedan
    las 3 Killer Queries originales (que ya no se usan para elegirlo).

Uso (desde la raiz del repo):
    py entrega_3/calibracion_umbral.py
Escribe entrega_3/resultados_calibracion.md
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from vector_db import KILLER_QUERIES, buscar_alquiherramientas, obtener_coleccion  # noqa: E402

SALIDA_MD = Path(__file__).resolve().parent / "resultados_calibracion.md"

# (consulta, documento esperado). Mezcla de fichas y politicas, con jerga y sin ella.
POSITIVAS_CALIBRACION = [
    ("quiero hacer unos agujeros en la pared para colgar una repisa", "DOC-001"),
    ("tienen algo para lavar la vereda y el auto", "DOC-003"),
    ("necesito dejar lisa una mesa de madera antes de barnizarla", "DOC-004"),
    ("tengo que cortar unos caños de hierro", "DOC-005"),
    ("quiero cortar placas de mdf derechitas", "DOC-006"),
    ("tengo que pintar la fachada de una casa de dos pisos", "DOC-007"),
    ("necesito romper un contrapiso", "DOC-008"),
    ("voy a hacer la mezcla para unas columnas", "DOC-009"),
    ("cuanta plata tengo que dejar de garantia", "DOC-010"),
    ("que papeles tengo que llevar para retirar", "DOC-011"),
    ("me lo pueden traer a mi casa", "DOC-012"),
    ("si cancelo la reserva me devuelven la plata", "DOC-013"),
]

POSITIVAS_VALIDACION = [
    ("abren el sabado a la tarde", "DOC-014"),
    ("se me rompio la maquina mientras la usaba, que hago", "DOC-015"),
    ("como uso las herramientas electricas sin lastimarme", "DOC-016"),
    ("necesito una mechadora para poner tarugos en el ladrillo", "DOC-001"),
    ("quiero sacarle el verdin al patio con agua a presion", "DOC-003"),
    ("tengo que cortar porcelanato", "DOC-005"),
    ("quiero sacar el revoque viejo que esta todo flojo", "DOC-008"),
    ("necesito una betonera para un fin de semana", "DOC-009"),
    ("hasta que hora puedo devolver la herramienta un viernes", "DOC-014"),
    ("que pasa si no voy a buscar la reserva y no aviso", "DOC-013"),
    ("necesito algo para trabajar en altura arreglando el techo", "DOC-007"),
    ("si devuelvo la amoladora con un golpe me cobran", "DOC-010"),
]

# Negativas: el sistema deberia decir "no tengo eso". Las "cercanas" comparten vocabulario
# de obra/herramientas con el catalogo y son las que realmente ponen a prueba el umbral.
NEGATIVAS_CALIBRACION = [
    "necesito una motosierra para cortar un arbol",  # cercana
    "alquilan cortadoras de cesped",  # cercana
    "tienen soldadora electrica",  # cercana
    "necesito una escalera de 7 metros",  # cercana
    "cual es la capital de francia",
    "me recomendas una receta de empanadas",
    "como esta el clima mañana en cordoba",
    "venden pintura latex para exterior",  # cercana (vende, no alquila)
]

NEGATIVAS_VALIDACION = [
    "alquilan un compresor de aire para pintar con soplete",  # cercana
    "tienen grupo electrogeno",  # cercana (sinonimo de la Killer Query 3)
    "necesito un elevador de autos para el taller",  # cercana
    "alquilan carpas para un evento",  # cercana
    "quien gano el partido de river ayer",
    "como hago para sacar el pasaporte",
    "me ayudas con la tarea de matematica",
    "tienen bordeadora para el pasto",  # cercana
]


def mejor_distancia(coleccion, consulta: str) -> tuple[float, str]:
    # umbral_distancia=None: para calibrar necesitamos la distancia cruda, sin cortar nada.
    r = buscar_alquiherramientas(coleccion, consulta, n_resultados=1, umbral_distancia=None)
    return r["distances"][0][0], r["ids"][0][0]


def medir(coleccion, positivas, negativas):
    pos = []
    for consulta, esperado in positivas:
        dist, doc = mejor_distancia(coleccion, consulta)
        pos.append({"consulta": consulta, "esperado": esperado, "top1": doc, "dist": dist})
    neg = []
    for consulta in negativas:
        dist, doc = mejor_distancia(coleccion, consulta)
        neg.append({"consulta": consulta, "top1": doc, "dist": dist})
    return pos, neg


def evaluar(pos, neg, umbral: float) -> dict:
    tp = sum(p["dist"] <= umbral for p in pos)  # positiva aceptada
    fn = len(pos) - tp  # positiva rechazada (falso "no tengo eso")
    tn = sum(n["dist"] > umbral for n in neg)  # negativa rechazada
    fp = len(neg) - tn  # negativa aceptada (el riesgo de alucinar)
    rec_pos = tp / len(pos)
    rec_neg = tn / len(neg)
    return {"umbral": umbral, "tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "rec_pos": rec_pos, "rec_neg": rec_neg, "balanced": (rec_pos + rec_neg) / 2}


def elegir_umbral(pos, neg) -> dict:
    candidatos = [round(0.25 + i * 0.005, 3) for i in range(41)]  # 0.250 .. 0.450
    evaluados = [evaluar(pos, neg, u) for u in candidatos]
    mejor_score = max(e["balanced"] for e in evaluados)
    empatados = [e for e in evaluados if e["balanced"] == mejor_score]
    # Entre empatados, el punto medio del intervalo: maximiza el margen a ambos lados.
    return empatados[len(empatados) // 2], evaluados


def _tabla_consultas(titulo, pos, neg, umbral) -> list[str]:
    lineas = [f"### {titulo}", "", "| Tipo | Consulta | Top-1 | Esperado | Distancia | Decision con umbral |",
              "|---|---|---|---|---|---|"]
    for p in sorted(pos, key=lambda x: x["dist"]):
        ok_doc = "" if p["top1"] == p["esperado"] else " (doc incorrecto)"
        dec = "acepta" if p["dist"] <= umbral else "**rechaza (FN)**"
        lineas.append(f"| positiva | {p['consulta']} | {p['top1']}{ok_doc} | {p['esperado']} | {p['dist']:.4f} | {dec} |")
    for n in sorted(neg, key=lambda x: x["dist"]):
        dec = "rechaza" if n["dist"] > umbral else "**acepta (FP)**"
        lineas.append(f"| negativa | {n['consulta']} | {n['top1']} | — | {n['dist']:.4f} | {dec} |")
    return lineas + [""]


def main() -> None:
    coleccion = obtener_coleccion()

    print("Midiendo set de CALIBRACION...")
    pos_c, neg_c = medir(coleccion, POSITIVAS_CALIBRACION, NEGATIVAS_CALIBRACION)
    print("Midiendo set de VALIDACION (held-out)...")
    pos_v, neg_v = medir(coleccion, POSITIVAS_VALIDACION, NEGATIVAS_VALIDACION)

    elegido, curva = elegir_umbral(pos_c, neg_c)
    umbral = elegido["umbral"]
    val = evaluar(pos_v, neg_v, umbral)
    viejo_val = evaluar(pos_v, neg_v, 0.32)

    top1_ok = sum(p["top1"] == p["esperado"] for p in pos_c + pos_v)
    n_pos = len(pos_c) + len(pos_v)

    print(f"\nUmbral elegido sobre CALIBRACION: {umbral} (balanced accuracy {elegido['balanced']:.3f})")
    print(f"En VALIDACION: TP={val['tp']} FN={val['fn']} TN={val['tn']} FP={val['fp']} "
          f"balanced={val['balanced']:.3f}")
    print(f"Umbral viejo 0.32 en VALIDACION: balanced={viejo_val['balanced']:.3f}")
    print(f"Top-1 correcto en positivas: {top1_ok}/{n_pos}")

    kq = []
    for q in KILLER_QUERIES:
        dist, doc = mejor_distancia(coleccion, q["query"])
        kq.append((q["query"], doc, dist))

    max_pos = max(p["dist"] for p in pos_c)
    min_neg = min(n["dist"] for n in neg_c)

    lineas = [
        "# Recalibracion del umbral de aceptacion",
        "",
        f"**Fecha de corrida:** {date.today().isoformat()}  ",
        f"**Consultas:** {len(pos_c) + len(pos_v)} positivas y {len(neg_c) + len(neg_v)} negativas, "
        "ninguna repetida de las Killer Queries de la Entrega 2.  ",
        "**Metodo:** el umbral se elige SOLO con el set de calibracion (maximo balanced accuracy, "
        "punto medio entre empatados) y se mide sobre el set de validacion, que no participo.",
        "",
        "## Resultado",
        "",
        "| | Umbral | TP | FN | TN | FP | Recall positivas | Recall negativas | Balanced acc. |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| Calibracion | {umbral} | {elegido['tp']} | {elegido['fn']} | {elegido['tn']} | {elegido['fp']} | "
        f"{elegido['rec_pos']:.2f} | {elegido['rec_neg']:.2f} | {elegido['balanced']:.3f} |",
        f"| **Validacion (held-out)** | {umbral} | {val['tp']} | {val['fn']} | {val['tn']} | {val['fp']} | "
        f"{val['rec_pos']:.2f} | {val['rec_neg']:.2f} | **{val['balanced']:.3f}** |",
        f"| Validacion con el umbral viejo | 0.32 | {viejo_val['tp']} | {viejo_val['fn']} | {viejo_val['tn']} | "
        f"{viejo_val['fp']} | {viejo_val['rec_pos']:.2f} | {viejo_val['rec_neg']:.2f} | {viejo_val['balanced']:.3f} |",
        "",
        f"Peor positiva de calibracion: {max_pos:.4f} — mejor negativa de calibracion: {min_neg:.4f} "
        f"({'hay solapamiento' if max_pos >= min_neg else 'separacion limpia'}).  ",
        f"Top-1 correcto en las positivas: {top1_ok}/{n_pos}.",
        "",
        "## Killer Queries de la Entrega 2 (ya no se usan para elegir el umbral)",
        "",
        "| Consulta | Top-1 | Distancia | Con el umbral nuevo |",
        "|---|---|---|---|",
    ]
    for consulta, doc, dist in kq:
        lineas.append(f"| {consulta} | {doc} | {dist:.4f} | {'acepta' if dist <= umbral else 'rechaza'} |")
    lineas += ["", "## Detalle por consulta", ""]
    lineas += _tabla_consultas("Calibracion", pos_c, neg_c, umbral)
    lineas += _tabla_consultas("Validacion (held-out)", pos_v, neg_v, umbral)
    lineas += ["## Curva sobre calibracion", "", "| Umbral | Recall positivas | Recall negativas | Balanced |",
               "|---|---|---|---|"]
    for e in curva[::2]:
        lineas.append(f"| {e['umbral']:.3f} | {e['rec_pos']:.2f} | {e['rec_neg']:.2f} | {e['balanced']:.3f} |")

    SALIDA_MD.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nTabla escrita en {SALIDA_MD}")


if __name__ == "__main__":
    main()
