# Resultados RAGAS (Entrega 3, Parte C)

**Fecha de corrida:** 2026-10-19  
**Dataset:** `golden_dataset.json`, 10 preguntas (3 simples, 3 complejas, 2 de escape, 2 informales)  
**LLM juez de RAGAS:** `gemini-3.5-flash-lite` · **Embeddings:** `gemini-embedding-001`  

## C.2 / C.3 — Comparativa (promedio sobre las preguntas con métrica válida)

| Métrica | RAG básico (docs enteros, k=3, umbral) | Solo chunking (500/100, k=3, sin juez) | RAG avanzado (chunks 500/100, k=8 + juez LLM) | Delta (avanzado − básico) |
|---|---|---|---|---|
| Faithfulness | 0.810 | 0.720 | 0.760 | **-0.050** |
| Answer Relevancy | 0.767 | 0.754 | 0.692 | **-0.075** |
| Context Precision | 0.733 | 0.650 | 0.700 | **-0.033** |
| Context Recall | 0.900 | 0.800 | 0.800 | **-0.100** |
| *Hit rate de documentos esperados (sin LLM)* | 1.000 | 1.000 | 1.000 | +0.000 |

## Por tipo de pregunta

**simple**

| Métrica | basico | solo_chunks | avanzado |
|---|---|---|---|
| Faithfulness | 1.000 | 1.000 | 1.000 |
| Answer Relevancy | 0.911 | 0.902 | 0.924 |
| Context Precision | 1.000 | 0.833 | 1.000 |
| Context Recall | 1.000 | 1.000 | 1.000 |

**compleja**

| Métrica | basico | solo_chunks | avanzado |
|---|---|---|---|
| Faithfulness | 0.867 | 0.733 | 0.867 |
| Answer Relevancy | 0.867 | 0.866 | 0.869 |
| Context Precision | 0.667 | 0.667 | 0.667 |
| Context Recall | 1.000 | 1.000 | 1.000 |

**escape**

| Métrica | basico | solo_chunks | avanzado |
|---|---|---|---|
| Faithfulness | 0.250 | 0.000 | 0.000 |
| Answer Relevancy | 0.389 | 0.338 | 0.000 |
| Context Precision | 0.167 | 0.000 | 0.000 |
| Context Recall | 0.500 | 0.000 | 0.000 |

**informal**

| Métrica | basico | solo_chunks | avanzado |
|---|---|---|---|
| Faithfulness | 1.000 | 1.000 | 1.000 |
| Answer Relevancy | 0.778 | 0.780 | 0.771 |
| Context Precision | 1.000 | 1.000 | 1.000 |
| Context Recall | 1.000 | 1.000 | 1.000 |

## Sin las preguntas de escape

Las de escape tienen una respuesta correcta que es, a propósito, 'no sé': RAGAS la castiga en Answer Relevancy (respuesta evasiva) y Context Recall/Precision no tienen sentido sin contexto esperado. Esta vista muestra las 8 preguntas con respuesta en la base.

| Métrica | basico | solo_chunks | avanzado |
|---|---|---|---|
| Faithfulness | 0.950 | 0.900 | 0.950 |
| Answer Relevancy | 0.861 | 0.858 | 0.865 |
| Context Precision | 0.875 | 0.812 | 0.875 |
| Context Recall | 1.000 | 1.000 | 1.000 |

## Detalle por pregunta

### RAG básico (docs enteros, k=3, umbral)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| S1 | simple | DOC-014 | 1.000 | 0.923 | 1.000 | 1.000 | ¡Hola! Abrimos de lunes a viernes de 8 a 18 horas y los sábados de 8 a 13 horas [DOC-014]. Los domingos y feriados permanece cerrado [DOC-014]. |
| S2 | simple | DOC-005, DOC-016, DOC-011 | 1.000 | 0.929 | 1.000 | 1.000 | ¡Hola! Sí, los anteojos de seguridad vienen incluidos en el alquiler de la amoladora [DOC-005]. |
| S3 | simple | DOC-013 | 1.000 | 0.881 | 1.000 | 1.000 | Hola! Si cancelás con menos de 24 horas de aviso, tenés un cargo del 20% del valor del alquiler [DOC-013]. |
| C1 | compleja | DOC-007, DOC-003 | 0.600 | 0.875 | 0.000 | 1.000 | ¡Hola! Para pintar el frente de tu casa de 3 metros de alto te conviene alquilar el módulo de andamio tubular de 1.5 metros [DOC-007]. El andamio no incluye barandas de seguridad salvo que se pida expresamente, y se recomienda siempre para trabajos de más de dos metros de altura [DOC-007]. Antes de pintar, podés limpiar el frente con la hidrolavadora Karcher K4, que está pensada para frentes de casa, veredas, patios, rejas, autos y motos [DOC-003]. |
| C2 | compleja | DOC-015, DOC-010, DOC-013 | 1.000 | 0.796 | 1.000 | 1.000 | ¡Hola! Si la herramienta se rompe por desgaste normal o una falla del equipo (no por mal uso), tenés que avisar de inmediato y el local la reemplaza sin costo adicional cuando sea posible [DOC-015]. Sobre el depósito, todo alquiler requiere un depósito que se paga al retirar y se devuelve en su totalidad cuando se la entrega de vuelta en las mismas condiciones [DOC-010]. Si la herramienta vuelve con un daño que no es desgaste normal de uso, el costo de reparación se descuenta del depósito y, si lo supera, se cobra la diferencia [DOC-010]. |
| C3 | compleja | DOC-011, DOC-014, DOC-008 | 1.000 | 0.931 | 1.000 | 1.000 | ¡Hola! Los sábados podés ir de 8 a 13 horas [DOC-014]. Para retirar el martillo demoledor, tenés que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a tu nombre, y además se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. |
| E1 | escape | DOC-003, DOC-013, DOC-010 | 0.500 | 0.778 | 0.333 | 1.000 | ¡Hola! El precio del alquiler se informa en el local al confirmar la reserva [DOC-010]. |
| E2 | escape | DOC-007, DOC-011, DOC-005 | 0.000 | 0.000 | 0.000 | 0.000 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| I1 | informal | DOC-004, DOC-009, DOC-005 | 1.000 | 0.810 | 1.000 | 1.000 | ¡Hola! Sí, genera bastante polvo fino, por lo que se recomienda usarla con la bolsa colectora puesta y, si se puede, barbijo [DOC-004]. |
| I2 | informal | DOC-014, DOC-015, DOC-013 | 1.000 | 0.746 | 1.000 | 1.000 | Hola! Las devoluciones fuera de horario no están permitidas: si el horario de cierre se cumple antes de que puedas devolver la herramienta, se factura un día adicional de alquiler [DOC-014]. |

### Solo chunking (500/100, k=3, sin juez)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| S1 | simple | DOC-014#c0, DOC-007#c1, DOC-004#c1 | 1.000 | 0.879 | 1.000 | 1.000 | ¡Hola! El local abre de lunes a viernes de 8 a 18 horas y los sábados de 8 a 13 horas. Los domingos y feriados permanece cerrado, no hay retiro ni devolución esos días [DOC-014]. |
| S2 | simple | DOC-016#c0, DOC-005#c0, DOC-008#c1 | 1.000 | 0.882 | 0.500 | 1.000 | ¡Hola! Sí, la amoladora angular Dewalt viene con anteojos de seguridad incluidos en el alquiler [DOC-005]. |
| S3 | simple | DOC-013#c0, DOC-010#c0, DOC-011#c1 | 1.000 | 0.946 | 1.000 | 1.000 | Hola! Si cancelás con menos de 24 horas de aviso, tenés un cargo del 20% del valor del alquiler [DOC-013]. |
| C1 | compleja | DOC-007#c0, DOC-003#c0, DOC-012#c0 | 0.800 | 0.911 | 1.000 | 1.000 | ¡Hola! Para pintar el frente de tu casa que tiene 3 metros de alto, te conviene alquilar el módulo de andamio tubular de 1.5 metros [DOC-007]. El andamio no incluye barandas de seguridad salvo que se pida expresamente, y se recomienda siempre para trabajos de más de dos metros de altura [DOC-007]. Para limpiar el frente antes de pintar, podés usar la hidrolavadora Karcher K4, que es un equipo de limpieza a presión pensado para frentes de casa, veredas, patios, rejas, autos y motos [DOC-003]. |
| C2 | compleja | DOC-015#c0, DOC-010#c0, DOC-010#c1 | 0.400 | 0.775 | 1.000 | 1.000 | ¡Hola! Si la rotura es por desgaste normal o falla del equipo (y no por mal uso), avisando de inmediato se te reemplaza sin costo adicional cuando sea posible [DOC-015]. Sobre el depósito, se devuelve en su totalidad cuando entregás la herramienta de vuelta en las mismas condiciones [DOC-010]. Si vuelve con un daño que no es desgaste normal, el costo de reparación se descuenta de ahí [DOC-010]. |
| C3 | compleja | DOC-011#c0, DOC-014#c0, DOC-011#c1 | 1.000 | 0.913 | 0.000 | 1.000 | ¡Hola! Los sábados podés ir de 8 a 13 horas [DOC-014]. Para retirar tenés que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a nombre tuyo [DOC-011]. Como el martillo demoledor es una herramienta de riesgo alto, además se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. Sin estos requisitos completos, el mostrador no entrega la herramienta aunque la reserva ya esté confirmada en el sistema [DOC-011]. |
| E1 | escape | DOC-003#c0, DOC-005#c1, DOC-013#c0 | 0.000 | 0.676 | 0.000 | 0.000 | Hola! Los precios no se informan por este medio, eso se informa en el local al confirmar la reserva. |
| E2 | escape | DOC-007#c0, DOC-011#c0, DOC-005#c1 | 0.000 | 0.000 | 0.000 | 0.000 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| I1 | informal | DOC-004#c1, DOC-008#c1, DOC-004#c0 | 1.000 | 0.806 | 1.000 | 1.000 | Hola! Sí, genera bastante polvo fino, por lo que se recomienda usarla con la bolsa colectora puesta y, si se puede, barbijo [DOC-004]. |
| I2 | informal | DOC-014#c0, DOC-015#c0, DOC-013#c0 | 1.000 | 0.753 | 1.000 | 1.000 | Hola! Las devoluciones fuera de horario no están permitidas: si el horario de cierre se cumple antes de que puedas devolver la herramienta, se factura un día adicional de alquiler [DOC-014]. |

### RAG avanzado (chunks 500/100, k=8 + juez LLM)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| S1 | simple | DOC-014#c0 | 1.000 | 0.879 | 1.000 | 1.000 | ¡Hola! El local abre de lunes a viernes de 8 a 18 horas y los sábados de 8 a 13 horas. Los domingos y feriados permanece cerrado [DOC-014]. |
| S2 | simple | DOC-005#c0, DOC-016#c0 | 1.000 | 0.929 | 1.000 | 1.000 | ¡Hola! Sí, los anteojos de seguridad vienen incluidos en el alquiler de la amoladora [DOC-005]. |
| S3 | simple | DOC-013#c0 | 1.000 | 0.965 | 1.000 | 1.000 | ¡Hola! Si cancelás con menos de 24 horas de aviso, tenés un cargo del 20% del valor del alquiler [DOC-013]. |
| C1 | compleja | DOC-003#c0, DOC-007#c0 | 0.600 | 0.904 | 1.000 | 1.000 | Para llegar a los 3 metros de altura te conviene alquilar el módulo de andamio tubular de 1,5 metros (se necesitan varios módulos apilados para una torre completa), que no incluye barandas de seguridad salvo que se pida expresamente [DOC-007]. Para limpiar el frente de tu casa antes de pintar, te conviene usar la Hidrolavadora Karcher K4, que es un equipo de limpieza a presión pensado para frentes de casa [DOC-003]. |
| C2 | compleja | DOC-015#c0, DOC-016#c1, DOC-010#c0 | 1.000 | 0.771 | 1.000 | 1.000 | Si la rotura es por desgaste normal o una falla del equipo (no por mal uso), debés avisar de inmediato y el local la reemplaza sin costo adicional cuando sea posible [DOC-015]. Sobre el depósito, todo alquiler requiere un depósito que se paga al retirar y se devuelve en su totalidad cuando se la entrega de vuelta en las mismas condiciones [DOC-010]. |
| C3 | compleja | DOC-011#c0, DOC-014#c0 | 1.000 | 0.933 | 0.000 | 1.000 | ¡Hola! Los sábados el local abre de 8 a 13 horas [DOC-014]. Para retirar una herramienta hay que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a nombre del cliente [DOC-011]. Además, tratándose del martillo demoledor (que es una herramienta de riesgo alto), se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. |
| E1 | escape | — | 0.000 | 0.000 | 0.000 | 0.000 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| E2 | escape | — | 0.000 | 0.000 | 0.000 | 0.000 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| I1 | informal | DOC-004#c1, DOC-004#c0 | 1.000 | 0.794 | 1.000 | 1.000 | ¡Hola! Sí, genera bastante polvo fino, por lo que se recomienda usarla con la bolsa colectora puesta y, si se puede, barbijo [DOC-004]. |
| I2 | informal | DOC-014#c0 | 1.000 | 0.747 | 1.000 | 1.000 | Hola! Las devoluciones fuera de horario no están permitidas: si el horario de cierre se cumple antes de que puedas devolver la herramienta, se factura un día adicional de alquiler [DOC-014]. |
