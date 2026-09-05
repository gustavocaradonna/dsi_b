"""
evidencia_alucinacion.py - A.2 Replica de "El Proveedor Enojado".

Le pide al modelo que responda como si fuera el sistema de atencion de
AlquiHerramientas, SIN darle catalogo, precios ni disponibilidad.
Guarda la respuesta cruda en evidencia/alucinacion_raw.md para pegarla
en el informe y marcar ahi lo que el modelo invento.

    python evidencia_alucinacion.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Prompt SIN fuente de verdad: ni catalogo, ni stock, ni lista de precios.
PROMPT = """Actua como el sistema de atencion al cliente de AlquiHerramientas,
un local de alquiler de herramientas en Buenos Aires.

Un cliente escribe por WhatsApp: "Hola, tenes una hidrolavadora disponible para
el sabado? Cuanto sale por dos dias y cuanto es el deposito de garantia?"

Responde como lo haria el sistema."""


def main() -> None:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: falta GEMINI_API_KEY en .env", file=sys.stderr)
        sys.exit(1)

    from google import genai

    modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    cliente = genai.Client(api_key=api_key)
    respuesta = cliente.models.generate_content(model=modelo, contents=PROMPT)

    salida = Path("evidencia")
    salida.mkdir(exist_ok=True)
    destino = salida / "alucinacion_raw.md"
    destino.write_text(
        f"# A.2 - Evidencia de alucinacion (salida cruda)\n\n"
        f"**Modelo:** `{modelo}`  \n"
        f"**Fecha:** {datetime.now().isoformat(timespec='seconds')}\n\n"
        f"## Prompt enviado (sin fuente de verdad)\n\n```\n{PROMPT}\n```\n\n"
        f"## Respuesta del modelo\n\n{respuesta.text}\n",
        encoding="utf-8",
    )
    print(respuesta.text)
    print(f"\n---\nGuardado en {destino}")
    print("Ahora: pegar esta respuesta en informe.md (A.2) y MARCAR lo inventado.")


if __name__ == "__main__":
    main()
