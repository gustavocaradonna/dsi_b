# Resultados RAGAS (Entrega 3, Parte C) — `validacion_fix.json`

**Fecha del reporte:** 2026-11-02  
**Dataset:** `validacion_fix.json`, 5 preguntas: 0 simple, 5 compleja, 0 escape, 0 informal (5 complejas agregadas después de la 1.ª corrida, ver informe C.1)  
**LLM juez de RAGAS:** `gemini-3.1-flash-lite` · **Embeddings:** `gemini-embedding-001`  

## C.2 / C.3 — Comparativa (promedio sobre las preguntas con métrica válida)

| Métrica | RAG básico (docs enteros, k=3, umbral) | RAG avanzado (chunks 500/100, k=8 + juez LLM) | Avanzado v2 (+ descomposición de consulta + documento padre) | Delta (avanzado − básico) | Delta (v2 − avanzado) | Delta (v2 − básico) |
|---|---|---|---|---|---|---|
| Faithfulness | 0.383 | 0.982 | 0.980 | **+0.598** | **-0.002** | **+0.597** |
| Answer Relevancy | 0.159 | 0.812 | 0.857 | **+0.653** | **+0.045** | **+0.698** |
| Context Precision | 0.000 | 0.000 | 0.000 | **+0.000** | **+0.000** | **+0.000** |
| Context Recall | 0.667 | 1.000 | 1.000 | **+0.333** | **+0.000** | **+0.333** |
| Context Precision por IDs (sin LLM) | 0.667 | 1.000 | 1.000 | **+0.333** | **+0.000** | **+0.333** |
| Context Recall por IDs (sin LLM) | 0.667 | 1.000 | 1.000 | **+0.333** | **+0.000** | **+0.333** |
| Hit rate de documentos esperados (sin LLM) | 0.667 | 1.000 | 1.000 | +0.333 | +0.000 | +0.333 |

Las dos métricas "por IDs" y el hit rate no usan LLM: se calculan sobre las preguntas con `docs_esperados` (en el golden, todas menos las 2 de escape).

## Por tipo de pregunta

**compleja**

| Métrica | basico | avanzado | avanzado_v2 |
|---|---|---|---|
| Faithfulness | 0.383 | 0.982 | 0.980 |
| Answer Relevancy | 0.159 | 0.812 | 0.857 |
| Context Precision | 0.000 | 0.000 | 0.000 |
| Context Recall | 0.667 | 1.000 | 1.000 |

## Sin las preguntas de escape

Las de escape tienen una respuesta correcta que es, a propósito, 'no sé': RAGAS la castiga en Answer Relevancy (respuesta evasiva) y Context Recall/Precision no tienen sentido sin contexto esperado. Esta vista muestra solo las preguntas con respuesta en la base.

| Métrica | basico | avanzado | avanzado_v2 |
|---|---|---|---|
| Faithfulness | 0.383 | 0.982 | 0.980 |
| Answer Relevancy | 0.159 | 0.812 | 0.857 |
| Context Precision | 0.000 | 0.000 | 0.000 |
| Context Recall | 0.667 | 1.000 | 1.000 |

## Detalle por pregunta

### RAG básico (docs enteros, k=3, umbral)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| V1 | compleja | DOC-008, DOC-015, DOC-014 | 0.667 | 0.000 | 0.000 | 0.667 | ¡Hola! Para romper el contrapiso te recomendamos el martillo demoledor Bosch GSH 5 [DOC-008]. Los sábados abrimos de 8 a 13 horas [DOC-014]. Con respecto a qué tenés que llevar para retirarla, eso se informa en el local al confirmar la reserva. |
| V2 | compleja | DOC-015, DOC-014, DOC-010 | 0.000 | 0.000 | 0.000 | 0.667 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| V3 | compleja | DOC-010, DOC-012, DOC-011 | 0.000 | 0.000 | 0.000 | 0.667 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| V4 | compleja | DOC-001, DOC-011, DOC-015 | 0.250 | 0.000 | 0.000 | 0.333 | ¡Hola! Para agujerear la pared y armar estanterías tenemos el taladro percutor Bosch GSB 550 [DOC-001]. Con respecto a los cuidados de seguridad y la cancelación para el día anterior, no poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| V5 | compleja | DOC-009, DOC-015, DOC-012 | 1.000 | 0.794 | 0.000 | 1.000 | ¡Hola! Te cuento sobre tus dudas: * **Limpieza:** Se recomienda limpiarla con agua apenas se termina de usar para que el cemento no se endurezca adentro [DOC-009]. * **Retiro a domicilio:** El retiro de vuelta también puede coordinarse a domicilio pagando el mismo adicional que el envío [DOC-012]. * **Roturas:** Si la herramienta se rompe durante el uso, debes avisar de inmediato [DOC-015]. Si la rotura es por desgaste normal o falla del equipo, el local la reemplaza sin costo adicional cuando sea posible [DOC-015]. Si es por mal uso o golpe evidente, se evalúa el costo contra el depósito de garantía [DOC-015]. En ningún caso debes intentar repararla por tu cuenta [DOC-015]. |

### RAG avanzado (chunks 500/100, k=8 + juez LLM)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| V1 | compleja | DOC-008#c0, DOC-011#c0, DOC-014#c0 | 1.000 | 0.928 | 0.000 | 1.000 | ¡Hola! Para romper el contrapiso te recomendamos el martillo demoledor Bosch GSH 5 [DOC-008]. Para retirarlo tenés que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a tu nombre. Al ser una herramienta de riesgo alto, además se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. Los sábados abrimos de 8 a 13 horas [DOC-014]. |
| V2 | compleja | DOC-004#c0, DOC-015#c0, DOC-014#c0 | 0.909 | 0.731 | 0.000 | 1.000 | ¡Hola! Para lijar y barnizar una mesa tenemos la lijadora orbital Makita BO3710, pensada para terminaciones finas en madera, preparar la superficie antes de pintar o barnizar, sacar pintura vieja o alisar bordes [DOC-004]. Sobre qué pasa si se rompe, si la rotura es por desgaste normal o una falla del equipo (no por mal uso), debés avisar de inmediato y el local la reemplaza sin costo adicional cuando sea posible; si es por mal uso o un golpe evidente, se evalúa el costo de reparación contra el depósito de garantía (y recordá que no debés intentar repararla por tu cuenta) [DOC-015]. Por último, los domingos el local permanece cerrado, por lo que no hay retiro ni devolución ese día [DOC-014]. |
| V3 | compleja | DOC-006#c0, DOC-010#c0, DOC-012#c0, DOC-010#c1 | 1.000 | 0.844 | 0.000 | 1.000 | ¡Hola! Qué tal. La sierra circular sirve para cortes rectos en placas de MDF [DOC-006]. Sobre el depósito de garantía, el monto varía según la herramienta y se informa junto con el precio antes de confirmar la reserva [DOC-010]. Podés pagarlo en efectivo, transferencia o con cupón de tarjeta de crédito [DOC-010]. En cuanto al envío, se hace dentro de un radio de la zona de cobertura con un costo adicional que depende de la distancia y se cotiza al confirmar la reserva [DOC-012]. |
| V4 | compleja | DOC-001#c0, DOC-013#c0, DOC-016#c0, DOC-001#c1 | 1.000 | 0.875 | 0.000 | 1.000 | ¡Hola! Para colgar estanterías tenemos el taladro percutor Bosch GSB 550 [DOC-001]. Sobre la seguridad, tenés que usar siempre los elementos de protección entregados con la herramienta (anteojos, protector de disco, guantes según corresponda), no usarla con las manos mojadas ni cerca de charcos, desconectarla antes de cambiar accesorios como mechas, y no dejarla al alcance de menores de edad [DOC-016]. Y respecto a la cancelación, una reserva se puede cancelar sin costo hasta 24 horas antes de la fecha de retiro [DOC-013]. |
| V5 | compleja | DOC-009#c1, DOC-015#c0, DOC-012#c0 | 1.000 | 0.681 | 0.000 | 1.000 | ¡Hola! Para limpiarla, se recomienda hacerlo con agua apenas terminás de usarla para que el cemento no se endurezca adentro [DOC-009]. El retiro de vuelta a domicilio puede coordinarse pagando el adicional correspondiente [DOC-012]. Si se rompe durante el uso, debés avisar de inmediato; si es por desgaste normal o falla, se reemplaza sin costo cuando sea posible, y nunca debés intentar repararla por tu cuenta [DOC-015]. |

### Avanzado v2 (+ descomposición de consulta + documento padre)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| V1 | compleja | DOC-011, DOC-014, DOC-008 | 1.000 | 0.906 | 0.000 | 1.000 | ¡Hola! Para romper un contrapiso, la herramienta recomendada es el martillo demoledor Bosch GSH 5 [DOC-008]. Para retirarla tenés que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a nombre tuyo. Además, al tratarse de una herramienta de riesgo alto, se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. Los sábados el local abre de 8 a 13 horas [DOC-014]. |
| V2 | compleja | DOC-015, DOC-014, DOC-004 | 0.900 | 0.886 | 0.000 | 1.000 | ¡Hola! Para lijar y barnizar una mesa tenemos la Lijadora orbital Makita BO3710, pensada para terminaciones finas en madera como preparar una superficie antes de pintar o barnizar, alisar bordes de muebles o pisos de madera [DOC-004]. Si la herramienta se rompe durante el uso por desgaste normal o falla del equipo (no por mal uso), debés avisar de inmediato y el local la reemplaza sin costo adicional cuando sea posible; si es por mal uso o golpe evidente, se evalúa el costo contra el depósito de garantía, y recordá que nunca debés intentar repararla por tu cuenta [DOC-015]. Sobre la devolución, los domingos el local permanece cerrado, por lo que no hay retiro ni devolución ese día [DOC-014]. |
| V3 | compleja | DOC-006, DOC-010, DOC-012 | 1.000 | 0.802 | 0.000 | 1.000 | ¡Hola! Sí, tenemos la sierra circular Makita 5007N que sirve para cortes rectos en placas de MDF [DOC-006]. El monto del depósito de garantía varía según la herramienta y se informa junto con el precio antes de confirmar la reserva [DOC-010]. Podés pagarlo en efectivo, transferencia o con cupón de tarjeta de crédito [DOC-010]. Respecto al envío, se hace dentro de un radio de la zona de cobertura con un costo adicional que depende de la distancia y se cotiza al confirmar la reserva [DOC-012]. |
| V4 | compleja | DOC-013, DOC-016, DOC-001 | 1.000 | 0.852 | 0.000 | 1.000 | ¡Hola! Para agujerear la pared tenemos el taladro percutor Bosch GSB 550, que sirve para instalar estanterías [DOC-001]. Sobre los cuidados de seguridad al usar herramientas eléctricas, tenés que usar siempre los elementos de protección entregados junto con la herramienta (anteojos, protector de disco, guantes según corresponda), no usarla con las manos mojadas ni cerca de charcos de agua, desconectarla antes de cambiar accesorios como discos o mechas, y no dejarla nunca al alcance de menores de edad. Ante cualquier chispa, olor a quemado o ruido anormal, hay que apagar la herramienta y avisar al local antes de seguir usándola [DOC-016]. Y con respecto a la cancelación, una reserva se puede cancelar sin costo hasta 24 horas antes de la fecha de retiro [DOC-013]. |
| V5 | compleja | DOC-009, DOC-012, DOC-015 | 1.000 | 0.838 | 0.000 | 1.000 | ¡Hola! Ahí te respondo tus dudas sobre la hormigonera: - Se recomienda limpiarla con agua apenas se termina de usar para que el cemento no se endurezca adentro [DOC-009]. - El retiro de vuelta a domicilio puede coordinarse pagando el mismo adicional que el envío [DOC-012]. - Si se rompe, tenés que avisar de inmediato; si es por desgaste normal o falla del equipo se reemplaza sin costo adicional cuando sea posible, y si es por mal uso o golpe se evalúa el costo contra el depósito de garantía [DOC-015]. Recordá que en ningún caso debés intentar repararla por tu cuenta [DOC-015]. Cualquier otra duda, avisame. |
