# Matriz de validación del agente (TP Final, Parte A)

**Fecha de corrida:** 2026-11-16 · **Modelo:** agente ReAct (LangGraph) + Gemini · **Límite de iteraciones:** 5 · corrida `0117dc`

| Escenario | Mensaje(s) del cliente | Comportamiento esperado | Herramientas usadas | Respuesta (enmascarada) | ¿Pasa? |
|---|---|---|---|---|---|
| 1. Conocimiento (RAG de la E3) | T1: ¿La hidrolavadora sirve para limpiar un techo de chapa? | Usa solo buscar_informacion (no toca SQL) y responde con el cuidado de la boquilla, citando DOC-003. | T1: buscar_informacion | T1: Sí, se puede usar, pero con precauciones: el chorro de alta presión directo puede levantar tornillos o dañar el sellador. Para techos de chapa se recomienda usar la boquilla de abanico ancho y baja presión, y nunca la boquilla puntual [DOC-003]. | **Sí** |
| 2. Sensor: stock insuficiente | T1: ¿Tienen 3 martillos demoledores del 2026-11-23 al 2026-11-24? | Usa consultar_disponibilidad y dice que NO alcanza (el stock total es 2): no inventa disponibilidad. | T1: consultar_disponibilidad | T1: No, para esas fechas tenemos disponibles solo 2 unidades de martillo demoledor (nuestro stock total es de 2). | **Sí** |
| 3. Actuador con memoria (2 turnos) | T1: Quiero reservar una hormigonera del 2026-11-28 al 2026-11-29<br>T2: Dale, mi teléfono es [TELEFONO] | Turno 1: falta el teléfono -> NO llama a crear_reserva y lo pide. Turno 2: recuerda herramienta y fechas (memoria), verifica stock y crea la reserva (1 fila nueva en SQL). El teléfono no aparece en la respuesta. | T1: consultar_disponibilidad<br>T2: crear_reserva | T1: Para avanzar con la reserva de la hormigonera del 2026-11-28 al 2026-11-29, ¿me pasarías tu número de teléfono de contacto?<br>T2: ¡Listo! Quedó creada la reserva pendiente (N° 1) para la Hormigonera electrica 150L del 2026-11-28 al 2026-11-29. El precio total es de $16.000 y el depósito de garantía es de $35.000. ¡Cualquier otra cosa que necesites, avisame! | **Sí** |
| 4. Fuera de dominio | T1: ¿Me pasás una receta de pizza a la piedra? | Cláusula de escape. Ninguna herramienta de SQL, ninguna reserva. | T1: — | T1: No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. | **Sí** |

**Resultado: 4/4 escenarios pasan.** Los chequeos son automáticos (herramientas usadas, filas nuevas en SQL, frase de escape), no una lectura a ojo.
