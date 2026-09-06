# TP Integrador — Entrega 1: AlquiHerramientas

**Asignatura:** Desarrollo de Sistemas de Inteligencia Artificial
**Grupo:** _(completar integrantes)_
**Dominio elegido:** Retail de servicios — alquiler de herramientas con atención por WhatsApp

---

# Parte A — Diagnóstico y Arquitectura

## A.1 — El caso

**AlquiHerramientas** es un local de alquiler de herramientas (taladros, hidrolavadoras,
lijadoras, andamios, hormigoneras) que atiende a particulares y contratistas de obra chica.
El 100% de la demanda entra por WhatsApp en texto libre y **una sola persona** responde a
mano: lee cada mensaje, se acuerda o consulta en una planilla qué hay disponible, busca el
precio en una lista impresa y anota la reserva en un cuaderno.

El proceso a automatizar es el **primer tramo**: interpretar el mensaje desestructurado y
extraer los datos operativos (qué herramienta, cuántas, para qué fechas, quién) que hoy una
persona tiene que deducir leyendo. Sobre esos datos ya estructurados, el sistema consulta la
base y responde con información real.

## A.2 — Evidencia de la necesidad (réplica de "El Proveedor Enojado")

Se le pidió a un modelo que respondiera **como el sistema de atención de AlquiHerramientas,
sin darle catálogo, ni lista de precios, ni stock**. La prueba se corrió dos veces con dos
modelos distintos, y el contraste entre ambas es el hallazgo más interesante de esta sección.

### Prueba 1 — Gemini 3.5 Flash vía API (`evidencia_alucinacion.py`)

Reproducible con `python evidencia_alucinacion.py`; la salida cruda con modelo y fecha queda
en [`evidencia/alucinacion_raw.md`](evidencia/alucinacion_raw.md).

**Prompt enviado** (sin ninguna fuente de verdad):

```
Actua como el sistema de atencion al cliente de AlquiHerramientas, un local de alquiler
de herramientas en Buenos Aires.

Un cliente escribe por WhatsApp: "Hola, tenes una hidrolavadora disponible para el sabado?
Cuanto sale por dos dias y cuanto es el deposito de garantia?"

Responde como lo haria el sistema.
```

**Respuesta del modelo, completa y textual:**

```
¡Hola! 👋 ¡Gracias por comunicarte con **AlquiHerramientas**! 🛠️

Sí, de momento tenemos disponibilidad de hidrolavadoras para este sábado. Trabajamos con
equipos de primera marca (Kärcher / Gamma) ideales para limpieza de frentes, patios y autos.

Te paso el detalle de lo que nos consultás para el fin de semana (sábado y domingo,
devolviendo el lunes a primera hora):

*   **Alquiler por 2 días:** $24.000 en total (te queda en $12.000 por día).
*   **Depósito de garantía:** $30.000. El mismo se puede realizar en efectivo, transferencia
    o mediante un cupón de tarjeta de crédito, y se te reintegra en su totalidad al momento
    de devolver la máquina en las mismas condiciones.

**Requisitos para el retiro:**
1. Presentar DNI físico.
2. Un servicio/impuesto a tu nombre que coincida con el domicilio del DNI (o contrato de
   alquiler).

Estamos en la zona de [San Cristóbal / Palermo / o tu barrio de preferencia en CABA],
abiertos el sábado de 8:00 a 13:00 hs. También contamos con servicio de envío a domicilio
con costo adicional si lo preferís. 😉

¿Te gustaría que te reservemos una para este sábado? Pasame tu nombre y lo coordinamos.
```

**Qué inventó y con qué nivel de confianza:**

| Dato afirmado | ¿De dónde salió? | Cómo lo presentó |
|---|---|---|
| "**Sí, de momento tenemos disponibilidad** de hidrolavadoras para este sábado" | Ninguna — no tiene acceso al calendario de reservas | Afirmación directa, sin ninguna reserva. Es el peor caso: confirma stock que no puede conocer. |
| **$24.000 por 2 días / $12.000 por día** | Ninguna — no existe lista de precios en el contexto | Cifras exactas, con el desglose hecho. Nada indica que sean estimadas. |
| **$30.000 de depósito de garantía** | Ninguna | Monto preciso + tres medios de pago + política de reintegro, todo inventado. |
| Marcas **Kärcher / Gamma** | Ninguna | Presentadas como "nuestros equipos de primera marca". |
| **Requisitos de retiro** (DNI + servicio a nombre propio) | Ninguna — es un procedimiento comercial que sólo el local define | Enumerados como política vigente del negocio. |
| **Horario sábado de 8:00 a 13:00** y servicio de envío | Ninguna | Afirmados sin condicional. |
| Ubicación | Ninguna | **Única vacilación de toda la respuesta:** puso `[San Cristóbal / Palermo / o tu barrio…]`. Es revelador — dudó del barrio, pero no del precio. |
| Ofrecimiento final de **tomar la reserva** | Ninguna | Se ofrece a ejecutar una acción de escritura sobre inventario que no puede realizar. |

**Nivel de confianza global: máximo.** El modelo no usó ni una sola vez "aproximadamente",
"consultá disponibilidad" o "sujeto a confirmación". Un cliente que recibe ese mensaje asume
razonablemente que tiene un precio en firme.

### Prueba 2 — otro modelo, misma consulta, comportamiento distinto

Se repitió la prueba en la interfaz web de otro modelo, con una consulta de taladro neumático:

```
Actuá como el sistema de atención de AlquiHerramientas.
Un usuario pregunta: "Tenés stock de taladro neumático para alquilar el 12/12 por 5 días?
Qué precio tiene?"

**Respuesta:**

¡Hola! Gracias por consultarnos 👋

Sí, trabajamos con taladros neumáticos (percutores/rotopercutores). Para reservarte el equipo
del **12/12 al 16/12 (5 días, devolución el 17/12 hasta las 12 hs)** necesitaría un par de datos:

- ¿Qué tipo de trabajo vas a hacer? (perforación en hormigón, demolición liviana, carrocería)
  — según eso te recomendamos el modelo
- ¿Contás con compresor propio? Si no, lo sumamos al alquiler (necesitás mínimo [X] HP / [X] L)

**Tarifa orientativa:**
- Taladro neumático: $[X] por día
- Combo 5 días con descuento: $[X] (en vez de $[X])
- Compresor [X] L: $[X] por día
- Depósito en garantía: $[X] (se devuelve al retorno del equipo en condiciones)

**Requisitos:** DNI, comprobante de domicilio y firma del contrato de alquiler. Retiro en
sucursal o envío con cargo dentro de zona.

Confirmame el modelo y te dejo la reserva tomada. Tenemos disponibilidad para esa fecha, pero
se asigna por orden de seña.

---

Los montos y la disponibilidad los dejé como placeholders porque no tengo acceso a tu catálogo
real. Si me pasás la lista de precios y el stock, te armo la respuesta lista para usar, o un
set de plantillas (con stock / sin stock / stock parcial) si estás armando el flujo del bot.
```

Este modelo **sí reconoció el límite**: dejó los montos como `$[X]` y aclaró al final que no
tiene acceso al catálogo. Pero igualmente inventó la estructura comercial del negocio —
combos con descuento por 5 días, requisitos de alquiler, servicios complementarios (compresor),
política de envío — y, sobre todo, **afirmó "Tenemos disponibilidad para esa fecha"**, el mismo
dato de stock que la Prueba 1. La cautela alcanzó para los precios, no para el inventario.

### Qué le faltó al modelo para responder bien

1. La tabla `herramientas`: existencia real del ítem en el catálogo, `precio_dia`, `deposito_garantia`.
2. La tabla `reservas`: qué está tomado en la ventana de fechas pedida.
3. La resolución de "el sábado" a una fecha calendario concreta.
4. Las políticas comerciales reales del local (requisitos, horarios, envíos), que no son datos
   de negocio derivables sino documentos — el material que en la Unidad 3 va a la base vectorial.

### Conclusión

El modelo no falla por ser malo: falla porque **la Base de Conocimiento no está en el sistema**.
Y las dos pruebas muestran que ni siquiera es un problema que se resuelva con un modelo mejor o
más prudente — el más cauto igual afirmó disponibilidad. Lo que sí queda claro es el modo de
falla: no dice "no sé", dice `$24.000` con total naturalidad. En un local de alquiler, un precio
inventado por WhatsApp es un compromiso comercial que el mostrador después tiene que desdecir,
y una disponibilidad inventada es un cliente que viaja hasta el local para encontrarse con que
la máquina no está.

## A.3 — PEAS extendido

| Pilar | Aplicado a AlquiHerramientas |
|---|---|
| **Performance** | (1) % de mensajes con intención correctamente clasificada (medido sobre `interacciones`); (2) % de solicitudes que pasan el contrato Pydantic sin intervención humana; (3) **cero respuestas con precio o disponibilidad no verificados contra la base** — métrica de veracidad, es la que más importa; (4) tiempo de primera respuesta < 30 s vs. las 2-4 h actuales; (5) % de reservas confirmadas sin repreguntar. |
| **Environment** | Canal de entrada: WhatsApp Business API (texto libre, en español rioplatense, con errores de tipeo, audios transcriptos y fotos). Sistemas con los que habla: la base PostgreSQL del local (`herramientas`, `clientes`, `reservas`), la planilla de precios que hoy vive en Excel y se migra a `herramientas`, y el celular del dueño para los casos escalados. Entorno **parcialmente observable** (el sistema no ve el mostrador físico: si alguien alquila presencialmente y no se carga, el stock queda desactualizado), **estocástico** y **secuencial**. |
| **Actuators** | (1) Enviar mensajes de WhatsApp; (2) escribir en `interacciones` (siempre, todas); (3) escribir en `reservas` con estado `pendiente` (acción de riesgo ALTO, la única que compromete inventario); (4) crear/actualizar `clientes`; (5) escalar a un humano notificando al dueño. **No puede**: confirmar una reserva, cobrar, aplicar descuentos ni modificar precios. |
| **Sensors** | Mensaje de texto libre + número de teléfono del remitente + timestamp, vía webhook de WhatsApp. A futuro: transcripción de audios y adjuntos (foto de la herramienta que el cliente busca). |
| **Base de Conocimiento** | **Hoy (Entrega 1): no existe.** Ese es exactamente el hallazgo de A.2. Lo que existe es el esquema SQL de B.5.b que la va a alojar: catálogo con precios y stock, historial de reservas y clientes. A futuro (Unidad 3): base vectorial con el manual de uso de cada herramienta, condiciones del contrato de alquiler y política de garantías, para responder preguntas que hoy ni el SQL resuelve ("¿la hidrolavadora sirve para limpiar un techo de chapa?"). |

## A.4 — Anatomía del token

Corrida real con `tiktoken` (`gpt-4o` encoding) — reproducible con
`python anatomia_token.py`:

| # | Consulta (ES) | Tokens ES | Tokens EN |
|---|---|---|---|
| 1 | ¡Buenas! ¿Tenés un taladro percutor disponible para el sábado que viene? | 19 | 13 |
| 2 | ¿Cuánto sale alquilar una hidrolavadora por dos días? | 14 | 14 |
| 3 | Quiero reservar una lijadora orbital del 10 al 12 de octubre. | 16 | 19 |
| | **Promedio** | **16.3** | **15.3** |

Sobrecosto del español sobre el mensaje del cliente: **+6.5%**.

**System Prompt** (lo que se paga en *cada* consulta, aunque el cliente escriba "hola"):

| Versión | Tokens |
|---|---|
| Zero-shot | 487 |
| Few-shot (3 ejemplos) | 740 (+253) |

**Reflexión.** El hallazgo contraintuitivo es que **la elección del idioma es casi irrelevante
frente al peso del prompt**. El mensaje del cliente son ~16 tokens; el System Prompt son 740.
El español "cuesta" 1 token más por mensaje (+6.5% sobre 16 tokens), pero el costo real por
consulta es 756 vs 755 tokens: **una diferencia del 0.1%**. Con 3.000 consultas/día a
USD 0.30/M tokens de entrada, traducir todo al inglés ahorraría **USD 0.33 al año**; sacar los
ejemplos few-shot ahorraría **USD 83 al año** (248 → 165). Conclusión operativa: no vale la pena
degradar la experiencia traduciendo, sí vale la pena vigilar el tamaño del prompt — y en cuanto
el catálogo entre al contexto (Unidad 3), esa será la variable que domine el costo. Es
precisamente el argumento a favor de RAG: recuperar sólo las 2 herramientas relevantes en vez
de inyectar las 40 del catálogo en cada mensaje.

---

# Parte B — Brief de Solución Técnica

## B.1 — Señal de dolor

**Latencia humana**, con **volumen repetitivo** como agravante.

Quien lo sufre: el dueño (que atiende el mostrador *y* el WhatsApp) y el cliente que espera.
Frecuencia: ~80-120 mensajes por día, con picos jueves y viernes (todo el mundo alquila para
el fin de semana), que es justo cuando el mostrador está más ocupado.

Consecuencia concreta de no resolverlo: un mensaje que se responde 3 horas después es una
herramienta que se alquiló en el local de enfrente. El pico de demanda y el pico de
indisponibilidad del que responde son **el mismo momento** — el negocio pierde ventas
exactamente cuando más hay para vender. Además, ~40% de los mensajes son las mismas tres
preguntas (¿tenés X?, ¿cuánto sale?, ¿me lo guardás?).

## B.2 — Usuario objetivo

**Usuario primario:** el cliente final — particular haciendo una refacción o contratista de
obra chica. Escribe desde el celular, con prisa y sin formato: "hola tenes hidro para el finde".

**Usuario operativo:** el dueño/encargado. **Hoy, sin IA:** lee el mensaje, interpreta qué
herramienta quiere, se fija en una planilla Excel qué hay, busca el precio en una lista
impresa, contesta a mano y anota la reserva en un cuaderno. Cuatro sistemas, ninguno conectado,
todos en su cabeza.

## B.3 — Matriz de Mapeo de Intenciones

| Entrada del usuario (caos) | Intención (LLM) | Parámetros (LLM) | Acción de backend (determinista) | Riesgo |
|---|---|---|---|---|
| "Buenas! Tenés un taladro percutor disponible para el sábado?" | `consultar_disponibilidad` | `herramienta`, `fecha_inicio`, `cantidad` | `SELECT` de stock menos reservas solapadas en la ventana de fechas | **BAJO** — sólo lee. El peor caso es informar "no hay" cuando había: se pierde una venta, no se compromete inventario. |
| "cuanto sale alquilar una hidrolavadora por dos dias?" | `consultar_precio` | `herramienta`, `dias_alquiler` (derivado de fechas) | `SELECT precio_dia, deposito_garantia` + cálculo aritmético en código | **MEDIO** — sólo lee, pero el output es un **compromiso comercial**. Un precio mal informado el local lo tiene que sostener o desdecir en el mostrador. El monto nunca lo calcula el LLM: lo multiplica el backend. |
| "Quiero reservar una lijadora del 10 al 12, soy Juan, 11-6543-2211" | `solicitar_reserva` | `herramienta`, `fecha_inicio`, `fecha_fin`, `cantidad`, `telefono_cliente` | `INSERT` en `reservas` con estado `pendiente` + `UPSERT` en `clientes` + aviso al dueño | **ALTO** — **escribe** y bloquea inventario físico. Una reserva mal extraída inmoviliza una herramienta que otro cliente pagaba, o hace que alguien viaje al local a buscar algo que no está. Por eso el contrato exige herramienta y fecha, y el estado nace en `pendiente`: la confirmación es humana. |
| "hola necesito algo para el finde" / "esto es un desastre, hace 3 hs que espero" | `fuera_de_alcance` | `requiere_humano = true` | No ejecuta nada: registra en `interacciones` y notifica al dueño | **BAJO** — es la válvula de escape. El riesgo real sería *no tenerla*: forzar al modelo a elegir una de las otras tres lo empuja a adivinar. |

> **Regla de oro aplicada:** el LLM nunca decide si hay stock ni cuánto sale. Extrae *qué* le
> preguntaron y *con qué parámetros*; el SQL responde. La IA es el intérprete, la base es la autoridad.

## B.4 — Decisión técnica: ¿Reglas o LLM?

| Componente | Determinista / Probabilístico | Justificación |
|---|---|---|
| Interpretar el mensaje de WhatsApp | **LLM** | Es lenguaje natural sin estructura, con jerga ("hidro", "el finde"), errores de tipeo y elipsis. No hay regex que cubra la variabilidad de cómo la gente pide un taladro. Es el caso canónico del diagrama de decisión: *requiere entender lenguaje natural → LLM*. |
| Clasificar la intención | **LLM** | Misma razón, pero **con el espacio de salida cerrado**: el `Literal` de 4 valores convierte una tarea abierta en una clasificación acotada y auditable. |
| Normalizar "hidro" → `hidrolavadora` | **Determinista** (`CATALOGO_ALIAS` en `schemas.py`) | Es un diccionario finito y conocido. Dejárselo al LLM introduce variabilidad gratis en un problema que una tabla de alias resuelve con certeza y a costo cero. |
| Validar el formato del teléfono y las fechas | **Determinista** (`@field_validator`) | La respuesta es binaria: cumple E.164 / ISO-8601 o no. Un LLM puede equivocarse; una regex no. |
| Resolver "el sábado" → `2026-09-12` | **Híbrido**: el LLM propone, el código verifica | Requiere entender la referencia relativa (LLM), pero el resultado debe ser una fecha válida — el validador rechaza cualquier cosa que no sea `YYYY-MM-DD`. El LLM puede sugerir; no puede colar basura. |
| Verificar stock disponible | **Determinista** (SQL) | Es un conteo sobre el estado real del mundo. **Ningún LLM puede saberlo** y si lo intenta, alucina: es exactamente lo que demostró A.2. |
| Calcular el precio total | **Determinista** (SQL + aritmética) | Es una multiplicación. Los LLM son notoriamente poco confiables en aritmética y acá el error tiene consecuencia financiera directa. *La respuesta es matemática → código.* |
| Escribir la reserva | **Determinista** (INSERT con constraints) | Operación transaccional con reglas de integridad (`fecha_fin >= fecha_inicio`, stock no negativo). El LLM jamás toca la base. |
| Redactar la respuesta al cliente | **LLM** | Generar lenguaje natural amable y contextual es literalmente para lo que sirve — pero sobre datos que ya vienen verificados del SQL, no inventados. |

## B.5 — Los tres artefactos de la especificación

### a) Contrato de datos (JSON de la API)

```json
POST /api/v1/mensajes

{
  "canal": "whatsapp",
  "telefono_remitente": "+5491165432211",
  "texto_libre": "Hola, tenés un taladro percutor para el sábado?",
  "adjuntos": [],
  "timestamp": "2026-09-05T14:32:10-03:00",
  "mensaje_id": "wamid.HBgNNTQ5MTE2NTQzMjIxMRUCABIYFj..."
}
```

| Campo | Por qué está |
|---|---|
| `canal` | El sistema nace en WhatsApp pero el dueño ya pidió Instagram. Fijar el canal desde el día uno evita rehacer el contrato; además el canal condiciona el largo y el tono de la respuesta. |
| `telefono_remitente` | Es la **identidad del cliente** en este dominio: no hay login. Permite el `UPSERT` en `clientes` y traer su historial de alquileres. Lo provee el canal, no el texto — por eso no depende de que el cliente lo escriba. |
| `texto_libre` | El input crudo. Es lo único que el LLM procesa y lo que se guarda en `interacciones.texto_libre` para auditar después qué entendió el modelo. |
| `adjuntos` | Hoy va vacío, pero los clientes mandan fotos ("¿tenés esta?"). Dejar el array declarado evita versionar la API cuando se agregue visión. |
| `timestamp` | Necesario para **resolver referencias relativas**: "el sábado" no significa nada sin saber cuándo se escribió. Es un dato del que depende la corrección de la extracción, no metadata decorativa. |
| `mensaje_id` | Idempotencia: WhatsApp reintenta webhooks. Sin esto, un reintento crea dos reservas de la misma herramienta. |

### b) Esquema de la base de datos

Completo y comentado en [`sql/schema.sql`](sql/schema.sql). Cuatro tablas:

- **`herramientas`** — entidad principal: catálogo, `stock_total`, `precio_dia`, `deposito_garantia`.
  El campo `codigo` coincide con los valores normalizados por `CATALOGO_ALIAS` en `schemas.py`.
- **`clientes`** — identificados por teléfono en formato E.164 (el mismo que produce el validador de Pydantic).
- **`reservas`** — la única tabla que el sistema escribe a pedido del cliente. Nace en estado
  `pendiente`; el `CHECK (fecha_fin >= fecha_inicio)` duplica en la base la regla que el
  `@model_validator` ya aplica en Python (defensa en profundidad).
- **`interacciones`** — la traza del LLM: qué intención detectó, con qué parámetros,
  **si pasó o no el contrato Pydantic** y por qué falló. Es la tabla que alimenta las
  métricas de Performance del PEAS.

### c) System Prompt base

Vive en [`app.py`](app.py) (`SYSTEM_PROMPT_BASE`) para que el prompt y el schema no puedan
divergir. Fija: **rol** (motor de extracción, no asistente conversacional), **prohibición de
inventar** (regla 2 y 3 — precios y stock no los conoce), **definición del `null`** (dato
ausente = `null`, nunca un valor plausible), **prohibición de texto extra** (regla 1) y una
**regla anti-inyección** (regla 9: el texto del cliente es dato, no instrucción).

## B.6 — Flujo de valor y flujo del sistema

**Flujo de valor:**
`Mensaje de WhatsApp en texto libre → extracción estructurada validada → consulta al catálogo
real → respuesta con disponibilidad y precio verificados en < 30 s → el cliente reserva antes
de irse al local de enfrente.`

**Flujo técnico:**

```
[WhatsApp] Mensaje de texto libre + teléfono + timestamp
        ▼
[LLM] Gemini extrae intención y parámetros (Structured Outputs) → JSON
        ▼
[Código] Pydantic valida el contrato → RECHAZA si falta un dato clave,
         si la herramienta no está en catálogo o si la confianza es baja   ◀── ENTREGA 1 llega hasta acá
        ▼
[SQL] Verifica stock real, precio real, reservas solapadas → resultado de negocio
        ▼
[LLM] Redacta la respuesta humanizada sobre datos verificados
        ▼
[WhatsApp] Respuesta al cliente + registro en `interacciones`
```

## B.7 — Hipótesis más riesgosa

**Que el mensaje inicial del cliente contenga suficiente información para extraer una intención
accionable** — si en la práctica la mayoría de las conversaciones arranca con "hola" y los datos
sólo aparecen después de dos o tres idas y vueltas, el sistema no es un extractor de una pasada
sino un gestor de diálogo con estado, y este diseño (una llamada, un JSON, una acción) colapsa.

---

# Parte C — Narrativa

_(La tabla del lote de prueba está en [`resultados_lote.md`](resultados_lote.md);
el contrato en [`schemas.py`](schemas.py) y el pipeline en [`app.py`](app.py).)_

## C.4 — Técnica de prompting

**Se usó Few-shot con 3 ejemplos.** Ambas corridas están en el repositorio y son reproducibles:
[`resultados_lote.md`](resultados_lote.md) (few-shot) y
[`resultados_zeroshot.md`](resultados_zeroshot.md) (zero-shot), con el mismo lote, el mismo
modelo (`gemini-3.5-flash-lite`) y temperatura 0.

### El caso que falla en Zero-shot y pasa con Few-shot

**Caso #4 — "hola necesito algo para el finde, me pasas info?"**

| | Zero-shot | Few-shot |
|---|---|---|
| `intencion` | `fuera_de_alcance` | `fuera_de_alcance` |
| `confianza` | 0.4 | 0.4 |
| `requiere_humano` | **`false`** ❌ | **`true`** ✅ |
| Resultado | **ValidationError** — `confianza < 0.6 obliga a requiere_humano = true` | **Valida** |

En zero-shot el modelo hizo *casi* todo bien: entendió que el mensaje era ambiguo y se
autoasignó una confianza baja (0.4). Pero dejó `requiere_humano` en `false` — es decir,
reconoció que no estaba seguro y aun así no pidió ayuda. El `@model_validator` lo rechazó, que
es el comportamiento correcto pero significa que ese mensaje queda sin respuesta.

Con el ejemplo de `"hola"` en el prompt — que muestra explícitamente la combinación
`confianza: 0.3` + `requiere_humano: true` — el modelo aprende que **baja confianza y escalar a
un humano van juntos**. La regla 7 y la regla 8 del System Prompt ya lo decían en prosa, pero
por separado; el ejemplo las une en un solo patrón observable.

### Una segunda diferencia: la alucinación de `fecha_fin`

**Caso #1 — "Tenés un taladro percutor disponible para el sábado?"**

| | Zero-shot | Few-shot |
|---|---|---|
| `fecha_inicio` | `2026-09-12` | `2026-09-12` |
| `fecha_fin` | **`2026-09-12`** ❌ | **`null`** ✅ |
| `dias_alquiler` | 1 | `None` |

El cliente nunca dijo hasta cuándo. En zero-shot el modelo **completó el hueco** con una fecha
de devolución inventada — asumió alquiler de un día. Es una alucinación silenciosa: el JSON
valida, el pipeline la deja pasar y el backend termina cotizando una ventana que el cliente
nunca pidió. El ejemplo de la amoladora, con `fecha_fin: null` cuando sólo se menciona una
fecha, corrige exactamente eso.

Este caso es más preocupante que el #4 justamente porque **no rompe nada**: el contrato no
lo puede atrapar, porque un `fecha_fin` inventado es sintácticamente perfecto. Es la clase de
error que sólo se detecta comparando corridas.

### Resultado global

| | Zero-shot | Few-shot |
|---|---|---|
| Validados | 4/6 | **5/6** |
| Rechazos por `ValidationError` | 2 (casos #4 y #6) | 1 (caso #6) |
| Alucinaciones que el contrato no atrapa | 1 (`fecha_fin` del #1) | 0 |

El único rechazo que queda en few-shot es el caso #6 (`motosierra` fuera de catálogo), que
**debe** ser rechazado: no es una falla, es el contrato haciendo su trabajo.

### Por qué no CoT

El razonamiento intermedio acá no agrega: la tarea es extracción, no inferencia en varios
pasos. Y con `response_mime_type: application/json` el modelo no tiene dónde escribir el
razonamiento sin romper el contrato. El costo del CoT (más tokens de salida, más latencia) no
se paga con precisión en una tarea de este tipo.

### Costo de la decisión

Los 3 ejemplos suman **253 tokens** al prompt (487 → 740), un ~50% más por consulta. Medido en
A.4: USD 83/año adicionales con 3.000 consultas diarias. A cambio, un caso ambiguo más
resuelto sin intervención humana y una alucinación de fecha eliminada. Se paga.

### Nota sobre la infraestructura

Durante las corridas aparecieron dos fallas reales de la API que vale la pena documentar
porque validan el manejo de errores del criterio C.2:

- **503 UNAVAILABLE** (modelo saturado) — transitorio. Se resolvió con reintentos y backoff
  exponencial; los reintentos quedan registrados en la salida del script.
- **429 RESOURCE_EXHAUSTED** — el free tier permite 20 requests por día y por modelo, y una
  primera tanda de reintectos agresivos la agotó. Se bajó el número de reintentos, se agregó
  una pausa de 5 s entre casos y se cambió a un modelo con cuota disponible.

En los tres casos el pipeline los clasificó como `ErrorDeRed` y **no** como `ValidationError`:
la separación entre "falló la infraestructura" y "el modelo violó el contrato" no es teórica,
se observó funcionando con tres tipos de error distintos.

## C.5 — Cierre: dónde se conecta

Este script es exactamente **los dos primeros pasos del flujo de B.6**: la llamada al LLM que
convierte texto libre en JSON, y la aduana de Pydantic que decide si ese JSON puede seguir. Lo
que produce es una `SolicitudAlquiler` validada — la estructura que el próximo eslabón consume.

**Lo que todavía le falta** es todo lo que está *debajo* de la línea punteada: no hay ninguna
consulta a `herramientas` ni a `reservas`, así que el sistema sabe *qué* le preguntaron pero
sigue sin poder responder *cuánto sale* ni *si hay*. Es decir: **sigue sin Base de Conocimiento,
igual que el modelo que alucinó en A.2** — con la diferencia crucial de que ahora, en vez de
inventar un precio, el sistema se detiene en un contrato que no puede cumplir. Cambiamos una
alucinación silenciosa por un rechazo explícito, que es un progreso real aunque todavía no sea
una respuesta.

Lo que sigue: cargar el catálogo real y conectar el SQL (respuesta verificada), y después
embeddings + RAG (Unidad 3) para las preguntas que el SQL no cubre —
"¿la hidrolavadora sirve para un techo de chapa?" no se contesta con un `SELECT`.
