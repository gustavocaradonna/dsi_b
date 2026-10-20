# Resultados RAGAS (Entrega 3, Parte C)

**Fecha de corrida:** 2026-10-19  
**Dataset:** `golden_dataset.json`, 13 preguntas: 3 simple, 6 compleja, 2 escape, 2 informal (3 complejas agregadas después de la 1.ª corrida, ver informe C.1)  
**LLM juez de RAGAS:** `gemini-3.1-flash-lite` · **Embeddings:** `gemini-embedding-001`  

## C.2 / C.3 — Comparativa (promedio sobre las preguntas con métrica válida)

| Métrica | RAG básico (docs enteros, k=3, umbral) | RAG avanzado (chunks 500/100, k=8 + juez LLM) | Delta (avanzado − básico) |
|---|---|---|---|
| Faithfulness | 0.685 | 0.690 | **+0.004** |
| Answer Relevancy | 0.597 | 0.665 | **+0.067** |
| Context Precision | 0.603 | 0.462 | **-0.141** |
| Context Recall | 0.872 | 0.795 | **-0.077** |
| Context Precision por IDs (sin LLM) | 0.667 (n=11) | 0.924 (n=11) | **+0.258** |
| Context Recall por IDs (sin LLM) | 0.939 (n=11) | 0.970 (n=11) | **+0.030** |
| Hit rate de documentos esperados (sin LLM) | 0.895 | 0.947 | +0.053 |

Las dos métricas "por IDs" y el hit rate no usan LLM: se calculan sobre las preguntas con `docs_esperados` (todas menos las 2 de escape).

## Por tipo de pregunta

**simple**

| Métrica | basico | avanzado |
|---|---|---|
| Faithfulness | 0.667 | 0.667 |
| Answer Relevancy | 0.906 | 0.910 |
| Context Precision | 1.000 | 1.000 |
| Context Recall | 1.000 | 1.000 |

**compleja**

| Métrica | basico | avanzado |
|---|---|---|
| Faithfulness | 0.874 | 0.883 |
| Answer Relevancy | 0.571 | 0.715 |
| Context Precision | 0.167 | 0.167 |
| Context Recall | 0.889 | 0.889 |

**escape**

| Métrica | basico | avanzado |
|---|---|---|
| Faithfulness | 0.000 | 0.000 |
| Answer Relevancy | 0.000 | 0.000 |
| Context Precision | 0.917 | 0.000 |
| Context Recall | 0.500 | 0.000 |

**informal**

| Métrica | basico | avanzado |
|---|---|---|
| Faithfulness | 0.833 | 0.833 |
| Answer Relevancy | 0.812 | 0.812 |
| Context Precision | 1.000 | 1.000 |
| Context Recall | 1.000 | 1.000 |

## Sin las preguntas de escape

Las de escape tienen una respuesta correcta que es, a propósito, 'no sé': RAGAS la castiga en Answer Relevancy (respuesta evasiva) y Context Recall/Precision no tienen sentido sin contexto esperado. Esta vista muestra solo las preguntas con respuesta en la base.

| Métrica | basico | avanzado |
|---|---|---|
| Faithfulness | 0.810 | 0.815 |
| Answer Relevancy | 0.706 | 0.786 |
| Context Precision | 0.545 | 0.545 |
| Context Recall | 0.939 | 0.939 |

## Solo las 10 preguntas originales

| Métrica | basico | avanzado |
|---|---|---|
| Faithfulness | 0.638 | 0.617 |
| Answer Relevancy | 0.698 | 0.696 |
| Context Precision | 0.783 | 0.600 |
| Context Recall | 0.900 | 0.800 |

## Solo las 3 complejas agregadas

| Métrica | basico | avanzado |
|---|---|---|
| Faithfulness | 0.843 | 0.933 |
| Answer Relevancy | 0.261 | 0.561 |
| Context Precision | 0.000 | 0.000 |
| Context Recall | 0.778 | 0.778 |

## Detalle por pregunta

### RAG básico (docs enteros, k=3, umbral)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| S1 | simple | DOC-014 | 1.000 | 0.886 | 1.000 | 1.000 | ¡Hola! Abrimos de lunes a viernes de 8 a 18 horas y los sábados de 8 a 13 horas [DOC-014]. Los domingos y feriados permanece cerrado [DOC-014]. |
| S2 | simple | DOC-005, DOC-016, DOC-011 | 1.000 | 0.894 | 1.000 | 1.000 | ¡Hola! Sí, los anteojos de seguridad vienen incluidos en el alquiler de la amoladora [DOC-005]. |
| S3 | simple | DOC-013 | 0.000 | 0.938 | 1.000 | 1.000 | Hola! Si cancelás con menos de 24 horas de aviso, tenés un cargo del 20% del valor del alquiler [DOC-013]. |
| C1 | compleja | DOC-007, DOC-003 | 0.714 | 0.875 | 0.000 | 1.000 | ¡Hola! Para pintar el frente de tu casa de 3 metros de alto te conviene alquilar el módulo de andamio tubular de 1.5 metros [DOC-007]. El andamio no incluye barandas de seguridad salvo que se pida expresamente, y se recomienda siempre para trabajos de más de dos metros de altura [DOC-007]. Antes de pintar, podés limpiar el frente con la hidrolavadora Karcher K4, que está pensada para frentes de casa, veredas, patios, rejas, autos y motos [DOC-003]. |
| C2 | compleja | DOC-015, DOC-010, DOC-013 | 1.000 | 0.833 | 1.000 | 1.000 | ¡Hola! Si la herramienta se rompe por desgaste normal o una falla del equipo (no por mal uso), tenés que avisar de inmediato y el local la reemplaza sin costo adicional cuando sea posible [DOC-015]. Sobre el depósito, todo alquiler requiere un depósito que se paga al retirar y se devuelve en su totalidad cuando se la entrega de vuelta en las mismas condiciones [DOC-010]. Si la herramienta vuelve con un daño que no es desgaste normal de uso, el costo de reparación se descuenta del depósito y, si lo supera, se cobra la diferencia [DOC-010]. |
| C3 | compleja | DOC-011, DOC-014, DOC-008 | 1.000 | 0.931 | 0.000 | 1.000 | ¡Hola! Los sábados podés ir de 8 a 13 horas [DOC-014]. Para retirar el martillo demoledor, tenés que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a tu nombre, y además se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. |
| C4 | compleja | DOC-005, DOC-011, DOC-016 | 0.778 | 0.000 | 0.000 | 0.667 | ¡Hola! Para retirar la amoladora vienen incluidos los anteojos de seguridad [DOC-005]. Además, como es una herramienta de riesgo alto, hay que firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. Para retirarla tenés que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a nombre tuyo [DOC-011]. No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| C5 | compleja | DOC-013, DOC-012, DOC-014 | 1.000 | 0.784 | 0.000 | 1.000 | ¡Hola! Una reserva se puede cancelar sin costo hasta 24 horas antes de la fecha de retiro [DOC-013]. Si no te presentas a retirar sin avisar, se cobra el alquiler del primer día completo y la reserva pasa a estado cancelada [DOC-013]. Sobre el envío a domicilio, se hace dentro de un radio de la zona de cobertura del local con un costo adicional que depende de la distancia y se cotiza al confirmar la reserva [DOC-012]. Para el andamio, que es una herramienta grande o pesada, el envío se recomienda fuertemente porque el traslado en auto particular puede ser complicado [DOC-012]. |
| C6 | compleja | DOC-014, DOC-003, DOC-011 | 0.750 | 0.000 | 0.000 | 0.667 | ¡Hola! Para usar la hidrolavadora necesitás una toma de agua cercana (canilla con rosca estándar) y un tomacorriente con puesta a tierra [DOC-003]. Sobre los domingos, el local permanece cerrado y no hay retiro ni devolución esos días [DOC-014]. Las devoluciones fuera de horario no están permitidas: si el horario de cierre se cumple antes de que el cliente pueda devolver la herramienta, se factura un día adicional de alquiler [DOC-014]. No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| E1 | escape | DOC-003, DOC-013, DOC-010 | 0.000 | 0.000 | 1.000 | 1.000 | ¡Hola! El precio del alquiler se informa en el local al confirmar la reserva [DOC-010]. |
| E2 | escape | DOC-007, DOC-011, DOC-005 | 0.000 | 0.000 | 0.833 | 0.000 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| I1 | informal | DOC-004, DOC-009, DOC-005 | 1.000 | 0.838 | 1.000 | 1.000 | ¡Hola! Sí, genera bastante polvo fino, por lo que se recomienda usarla con la bolsa colectora puesta y, si se puede, barbijo [DOC-004]. |
| I2 | informal | DOC-014, DOC-015, DOC-013 | 0.667 | 0.787 | 1.000 | 1.000 | Hola! Las devoluciones fuera de horario no están permitidas: si el horario de cierre se cumple antes de que puedas devolver la herramienta, se factura un día adicional de alquiler [DOC-014]. |

### RAG avanzado (chunks 500/100, k=8 + juez LLM)

| Id | Tipo | Contexto | Faith. | Ans. Rel. | Ctx. Prec. | Ctx. Rec. | Respuesta |
|---|---|---|---|---|---|---|---|
| S1 | simple | DOC-014#c0 | 1.000 | 0.879 | 1.000 | 1.000 | ¡Hola! El local abre de lunes a viernes de 8 a 18 horas y los sábados de 8 a 13 horas. Los domingos y feriados permanece cerrado [DOC-014]. |
| S2 | simple | DOC-005#c0, DOC-016#c0 | 1.000 | 0.926 | 1.000 | 1.000 | ¡Hola! Sí, los anteojos de seguridad vienen incluidos en el alquiler de la amoladora [DOC-005]. |
| S3 | simple | DOC-013#c0 | 0.000 | 0.924 | 1.000 | 1.000 | ¡Hola! Si cancelás con menos de 24 horas de aviso, tenés un cargo del 20% del valor del alquiler [DOC-013]. |
| C1 | compleja | DOC-003#c0, DOC-007#c0 | 0.667 | 0.919 | 0.000 | 1.000 | Para llegar a los 3 metros de altura te conviene alquilar el módulo de andamio tubular de 1,5 metros (se necesitan varios módulos apilados para una torre completa), que no incluye barandas de seguridad salvo que se pida expresamente [DOC-007]. Para limpiar el frente de tu casa antes de pintar, te conviene usar la Hidrolavadora Karcher K4, que es un equipo de limpieza a presión pensado para frentes de casa [DOC-003]. |
| C2 | compleja | DOC-015#c0, DOC-016#c1, DOC-010#c0 | 0.833 | 0.764 | 1.000 | 1.000 | Si la rotura es por desgaste normal o una falla del equipo (no por mal uso), debés avisar de inmediato y el local la reemplaza sin costo adicional cuando sea posible [DOC-015]. Sobre el depósito, todo alquiler requiere un depósito que se paga al retirar y se devuelve en su totalidad cuando se la entrega de vuelta en las mismas condiciones [DOC-010]. |
| C3 | compleja | DOC-011#c0, DOC-014#c0 | 1.000 | 0.922 | 0.000 | 1.000 | ¡Hola! Los sábados el local abre de 8 a 13 horas [DOC-014]. Para retirar una herramienta hay que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a nombre del cliente [DOC-011]. Además, tratándose del martillo demoledor (que es una herramienta de riesgo alto), se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. |
| C4 | compleja | DOC-005#c0, DOC-011#c0 | 0.800 | 0.000 | 0.000 | 0.333 | ¡Hola! Para retirar la amoladora te cuento lo siguiente: - Viene incluida con protector de disco puesto y se recomienda usar anteojos de seguridad, que también vienen incluidos en el alquiler [DOC-005]. - Tenés que presentar DNI físico y un comprobante de domicilio a nombre propio (factura de luz, gas o similar) o el contrato de alquiler si la vivienda no está a nombre tuyo [DOC-011]. - Al ser una herramienta de riesgo alto, además se pide firmar una constancia de que se explicaron las medidas de seguridad básicas [DOC-011]. Sobre si te la pueden llevar a casa, no poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local [DOC-005, DOC-011]. |
| C5 | compleja | DOC-013#c0, DOC-012#c0 | 1.000 | 0.811 | 0.000 | 1.000 | ¡Hola! Podés cancelar tu reserva sin costo hasta 24 horas antes de la fecha de retiro [DOC-013]. Si no te presentas a retirar sin avisar, se cobra el alquiler del primer día completo y la reserva pasa a estado cancelada [DOC-013]. Sobre el envío, se hace dentro de un radio de la zona de cobertura del local con un costo adicional que depende de la distancia y se cotiza al confirmar la reserva [DOC-012]. El retiro de vuelta también puede coordinarse a domicilio pagando el mismo adicional, y para herramientas grandes o pesadas como el andamio se recomienda fuertemente porque el traslado en auto particular puede ser complicado [DOC-012]. |
| C6 | compleja | DOC-003#c1, DOC-014#c0, DOC-015#c0 | 1.000 | 0.873 | 0.000 | 1.000 | ¡Hola! Para usar la hidrolavadora necesitás una toma de agua cercana (canilla con rosca estándar) y un tomacorriente con puesta a tierra [DOC-003]. Si la herramienta se rompe durante el uso por desgaste normal o falla del equipo, debés avisar de inmediato y el local la reemplaza sin costo adicional cuando sea posible [DOC-015]. Si la rotura es por mal uso o golpe evidente, se evalúa el costo de reparación contra el depósito [DOC-015]. Recordá que en ningún caso debés intentar repararla por tu cuenta [DOC-015]. Los domingos y feriados el local permanece cerrado, por lo que no hay retiro ni devolución esos días [DOC-014]. Tené en cuenta que las devoluciones fuera de horario no están permitidas: si el horario de cierre se cumple antes de que puedas devolverla, se factura un día adicional de alquiler [DOC-014]. |
| E1 | escape | — | 0.000 | 0.000 | 0.000 | 0.000 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| E2 | escape | — | 0.000 | 0.000 | 0.000 | 0.000 | No poseo información sobre eso en la base de AlquiHerramientas. Si querés, te comunico con una persona del local. |
| I1 | informal | DOC-004#c1, DOC-004#c0 | 1.000 | 0.837 | 1.000 | 1.000 | ¡Hola! Sí, genera bastante polvo fino, por lo que se recomienda usarla con la bolsa colectora puesta y, si se puede, barbijo [DOC-004]. |
| I2 | informal | DOC-014#c0 | 0.667 | 0.787 | 1.000 | 1.000 | Hola! Las devoluciones fuera de horario no están permitidas: si el horario de cierre se cumple antes de que puedas devolver la herramienta, se factura un día adicional de alquiler [DOC-014]. |
