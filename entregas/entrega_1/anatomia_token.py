"""
anatomia_token.py - A.4 Anatomia del token.

1) Compara el costo en tokens de consultas tipicas de AlquiHerramientas
   en espanol (como llegan realmente por WhatsApp) y en ingles.
2) Mide el System Prompt, que es lo que se paga en CADA consulta.

    python anatomia_token.py
"""

import tiktoken

from app import construir_system_prompt

enc = tiktoken.encoding_for_model("gpt-4o")

PARES = [
    (
        "¡Buenas! ¿Tenés un taladro percutor disponible para el sábado que viene?",
        "Hi! Do you have a hammer drill available for next Saturday?",
    ),
    (
        "¿Cuánto sale alquilar una hidrolavadora por dos días?",
        "How much does it cost to rent a pressure washer for two days?",
    ),
    (
        "Quiero reservar una lijadora orbital del 10 al 12 de octubre.",
        "I want to book an orbital sander from October 10th to the 12th.",
    ),
]

# Precio de referencia de un modelo flash (USD por millon de tokens de entrada).
PRECIO_POR_MILLON_INPUT = 0.30
CONSULTAS_POR_DIA = 3000


def tk(texto: str) -> int:
    return len(enc.encode(texto))


print(f"{'':4} {'ES':>5} {'EN':>5}  consulta")
print("-" * 80)
total_es = total_en = 0
for i, (es, en) in enumerate(PARES, start=1):
    t_es, t_en = tk(es), tk(en)
    total_es += t_es
    total_en += t_en
    print(f"{i:>3}. {t_es:>5} {t_en:>5}  {es}")

prom_es = total_es / len(PARES)
prom_en = total_en / len(PARES)
print("-" * 80)
print(f"Promedio  ES: {prom_es:.1f} tokens | EN: {prom_en:.1f} tokens")
print(f"Sobrecosto del espanol sobre el mensaje: {(prom_es / prom_en - 1) * 100:+.1f}%")

# El mensaje del cliente es la parte chica. El System Prompt viaja siempre.
sp_zero = tk(construir_system_prompt(few_shot=False))
sp_few = tk(construir_system_prompt(few_shot=True))
print(f"\nSystem Prompt zero-shot : {sp_zero} tokens")
print(f"System Prompt few-shot  : {sp_few} tokens (+{sp_few - sp_zero} por los ejemplos)")

for etiqueta, sp in (("zero-shot", sp_zero), ("few-shot", sp_few)):
    por_consulta_es = sp + prom_es
    por_consulta_en = sp + prom_en
    costo_es = CONSULTAS_POR_DIA * por_consulta_es / 1_000_000 * PRECIO_POR_MILLON_INPUT
    costo_en = CONSULTAS_POR_DIA * por_consulta_en / 1_000_000 * PRECIO_POR_MILLON_INPUT
    print(
        f"\n{etiqueta}: {por_consulta_es:.0f} tokens/consulta (ES) vs "
        f"{por_consulta_en:.0f} (EN)"
    )
    print(
        f"  {CONSULTAS_POR_DIA} consultas/dia a USD {PRECIO_POR_MILLON_INPUT}/M input: "
        f"ES USD {costo_es * 365:.2f}/anio | EN USD {costo_en * 365:.2f}/anio"
    )
