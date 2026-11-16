"""
matriz_validacion.py - Matriz de validacion del agente con 4 escenarios (TP Final, Parte A).

Corre el agente real (Gemini + herramientas + memoria SQLite) y verifica automaticamente, para cada
escenario, que herramientas uso y que hizo con ellas. Las fechas se calculan desde hoy, asi el
script sigue siendo valido cualquier dia que se corra.

    python evidencia/matriz_validacion.py      -> escribe evidencia/resultados_matriz.md
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.agente.servicio import Agente  # noqa: E402
from app.herramientas.conocimiento.indice import asegurar_indice  # noqa: E402
from app.shared import config, guardrails, sql  # noqa: E402

SALIDA_MD = Path(__file__).resolve().parent / "resultados_matriz.md"


def _proximo(dia_semana: int, desde: date | None = None) -> date:
    """Proximo lunes=0 ... domingo=6, estrictamente despues de hoy."""
    desde = desde or date.today()
    return desde + timedelta(days=(dia_semana - desde.weekday() - 1) % 7 + 1)


def _reservas_de(telefono: str) -> int:
    conn = sql.conectar()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM reservas r JOIN clientes c ON c.id = r.cliente_id WHERE c.telefono = ?",
            (telefono,),
        ).fetchone()[0]
    finally:
        conn.close()


def main() -> None:
    asegurar_indice()
    agente = Agente()
    sufijo = uuid.uuid4().hex[:6]  # threads nuevos en cada corrida: la matriz no hereda memoria vieja

    sabado = _proximo(5)
    inicio_martillo = sabado + timedelta(days=2)
    inicio_hormigonera = sabado + timedelta(days=7)
    telefono = "11" + str(40000000 + int(sufijo, 16) % 9999999).zfill(8)  # uno distinto por corrida

    escenarios = [
        {
            "nombre": "1. Conocimiento (RAG de la E3)",
            "turnos": ["¿La hidrolavadora sirve para limpiar un techo de chapa?"],
            "esperado": "Usa solo buscar_informacion (no toca SQL) y responde con el cuidado de la boquilla, citando DOC-003.",
            "chequeo": lambda r: (r[-1]["herramientas_usadas"] and set(r[-1]["herramientas_usadas"]) == {"buscar_informacion"}
                                  and "DOC-003" in r[-1]["respuesta"]),
        },
        {
            "nombre": "2. Sensor: stock insuficiente",
            "turnos": [f"¿Tienen 3 martillos demoledores del {inicio_martillo.isoformat()} al "
                       f"{(inicio_martillo + timedelta(days=1)).isoformat()}?"],
            "esperado": "Usa consultar_disponibilidad y dice que NO alcanza (el stock total es 2): no inventa disponibilidad.",
            "chequeo": lambda r: "consultar_disponibilidad" in r[-1]["herramientas_usadas"]
            and "crear_reserva" not in r[-1]["herramientas_usadas"],
        },
        {
            "nombre": "3. Actuador con memoria (2 turnos)",
            "turnos": [
                f"Quiero reservar una hormigonera del {inicio_hormigonera.isoformat()} al "
                f"{(inicio_hormigonera + timedelta(days=1)).isoformat()}",
                f"Dale, mi teléfono es {telefono[:2]} {telefono[2:6]} {telefono[6:]}",
            ],
            "esperado": "Turno 1: falta el teléfono -> NO llama a crear_reserva y lo pide. Turno 2: recuerda herramienta y "
            "fechas (memoria), verifica stock y crea la reserva (1 fila nueva en SQL). El teléfono no aparece en la respuesta.",
            "chequeo": lambda r: "crear_reserva" not in r[0]["herramientas_usadas"]
            and "crear_reserva" in r[1]["herramientas_usadas"]
            and _reservas_de(telefono) == 1
            and telefono[2:6] not in r[1]["respuesta_enmascarada"],
        },
        {
            "nombre": "4. Fuera de dominio",
            "turnos": ["¿Me pasás una receta de pizza a la piedra?"],
            "esperado": "Cláusula de escape. Ninguna herramienta de SQL, ninguna reserva.",
            "chequeo": lambda r: r[-1]["respuesta"].strip().startswith("No poseo información")
            and not ({"consultar_disponibilidad", "consultar_precio", "crear_reserva"} & set(r[-1]["herramientas_usadas"])),
        },
    ]

    lineas = [
        "# Matriz de validación del agente (TP Final, Parte A)",
        "",
        f"**Fecha de corrida:** {date.today().isoformat()} · **Modelo:** agente ReAct (LangGraph) + Gemini · "
        f"**Límite de iteraciones:** {config.MAX_ITERACIONES} · corrida `{sufijo}`",
        "",
        "| Escenario | Mensaje(s) del cliente | Comportamiento esperado | Herramientas usadas | Respuesta (enmascarada) | ¿Pasa? |",
        "|---|---|---|---|---|---|",
    ]
    aprobados = 0
    for esc in escenarios:
        thread = f"matriz-{sufijo}-{esc['nombre'][0]}"
        resultados = []
        for turno in esc["turnos"]:
            r = agente.consultar(thread, turno)
            r["respuesta_enmascarada"] = guardrails.enmascarar_datos_personales(r["respuesta"]).texto
            resultados.append(r)
            print(f"[{esc['nombre']}] {turno}\n  herramientas={r['herramientas_usadas']}\n  -> {r['respuesta_enmascarada']}\n")
        paso = bool(esc["chequeo"](resultados))
        aprobados += paso
        mensajes = "<br>".join(f"T{i + 1}: {guardrails.enmascarar_datos_personales(t).texto}" for i, t in enumerate(esc["turnos"]))
        herramientas = "<br>".join(f"T{i + 1}: {', '.join(r['herramientas_usadas']) or '—'}" for i, r in enumerate(resultados))
        respuestas = "<br>".join(
            f"T{i + 1}: " + " ".join(r["respuesta_enmascarada"].split()).replace("|", "\\|") for i, r in enumerate(resultados)
        )
        lineas.append(f"| {esc['nombre']} | {mensajes} | {esc['esperado']} | {herramientas} | {respuestas} | "
                      f"{'**Sí**' if paso else '**No**'} |")

    lineas += ["", f"**Resultado: {aprobados}/{len(escenarios)} escenarios pasan.** Los chequeos son automáticos "
               "(herramientas usadas, filas nuevas en SQL, frase de escape), no una lectura a ojo.", ""]
    SALIDA_MD.write_text("\n".join(lineas), encoding="utf-8")
    print(f"{aprobados}/{len(escenarios)} escenarios pasan. Tabla en {SALIDA_MD}")


if __name__ == "__main__":
    main()
