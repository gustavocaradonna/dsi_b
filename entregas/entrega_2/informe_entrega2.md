# TP Integrador — Entrega 2: Base de Conocimiento Vectorial

**Asignatura:** Desarrollo de Sistemas de Inteligencia Artificial

**Dominio:** AlquiHerramientas — mismo dominio de la Entrega 1 (alquiler de herramientas por WhatsApp)

**Proveedor de embeddings:** Gemini (`gemini-embedding-001`), reusando la `GEMINI_API_KEY` ya
configurada en la Entrega 1 — sin credenciales nuevas.

---

# Parte A — Embeddings y Búsqueda Semántica

## A.1 — Autopsia del contexto estático

| Problema | Aplicado a AlquiHerramientas |
|---|---|
| **Desangre de tokens** | La base tiene 16 documentos. Pasarlos todos en el System Prompt de cada consulta cuesta **1823 tokens** (medido con `tiktoken`, encoding de `gpt-4o`), contra **137 tokens** del único documento realmente relevante para una consulta puntual (`DOC-008`, martillo demoledor) — **13 veces más**. Con 3.000 consultas/día a USD 0,30/M tokens de entrada (la misma tarifa de referencia usada en A.4 de la Entrega 1): pasar los 16 documentos completos sale ≈USD 599/año; recuperar solo los 2-3 relevantes (≈400 tokens) sale ≈USD 131/año. Y esto es con un catálogo de **16** ítems — el negocio real tiene más herramientas, más políticas, más variantes por sucursal: el costo crece lineal con el catálogo, la recuperación semántica no. |
| **Lost in the Middle** | Si los 16 documentos se pegan en un solo bloque de contexto, una pregunta puntual como "¿cuánto tengo que dejar de depósito?" puede perder la respuesta si `DOC-010` (la política de depósito) queda en la mitad del bloque entre las 9 fichas de herramienta y las otras 6 políticas — el modelo tiende a prestar más atención al principio y al final del contexto, no a lo que está en el medio, sin importar que la respuesta correcta esté ahí, completa y sin ambigüedad. |
| **Inconsistencia de estado concurrente** | El campo `activo` de una herramienta (p. ej. si la sierra circular está en service, ver B.3) puede cambiar mientras un cliente está a mitad de una conversación de WhatsApp. Un System Prompt armado al inicio de la sesión con "sierra circular: activa" queda desactualizado si en el medio otro proceso marca la herramienta como inactiva — el prompt es una foto fija, la base vectorial (o el SQL) se puede consultar en cada turno. |

**Cierre.** Un `SELECT ... WHERE descripcion LIKE '%pared%'` tampoco resuelve esto porque busca
coincidencia literal de substring, no significado: la Killer Query 1 de B.6 (más abajo) pregunta
por "picar los cascotes de un piso viejo antes de embaldosar" y el documento correcto
(`DOC-008`, martillo demoledor) no contiene ni "cascotes" ni "embaldosar" en su texto. Un `LIKE`
no encuentra nada; la búsqueda semántica lo encuentra primero, con la distancia más baja de las
tres candidatas.

## A.2 — Similitud coseno a mano

Se redujo el dominio a 2 ejes con sentido: **eje X = potencia / uso pesado**, **eje Y = uso
hogareño / liviano**. Documentos y consulta, calculados en 3 pasos y validados con NumPy
(`pipeline_vectorial.py --cosine-a-mano`, corrida real):

```
Consulta: [8.0, 2.0]  ('necesito romper una pared de material')

  martillo_demoledor (romper pared)  vector=[9.0, 1.0]
    paso 1  A . B              = 74.0000
    paso 2  ||A|| x ||B||      = 8.2462 x 9.0554 = 74.6726
    paso 3  similitud = paso1/paso2 = 0.9910   (validado con NumPy: 0.9910)

  taladro (perforar)  vector=[6.0, 7.0]
    paso 1  A . B              = 62.0000
    paso 2  ||A|| x ||B||      = 8.2462 x 9.2195 = 76.0263
    paso 3  similitud = paso1/paso2 = 0.8155   (validado con NumPy: 0.8155)

  lijadora (terminaciones finas)  vector=[2.0, 8.0]
    paso 1  A . B              = 32.0000
    paso 2  ||A|| x ||B||      = 8.2462 x 8.2462 = 68.0000
    paso 3  similitud = paso1/paso2 = 0.4706   (validado con NumPy: 0.4706)
```

El orden (martillo > taladro > lijadora) es exactamente el que un local de alquiler esperaría
para esa consulta: la herramienta pensada para romper pared gana con 0.99, la que perfora (pero
no rompe) queda a mitad de camino con 0.82, y la de terminaciones finas, que no tiene nada que
ver, cae a 0.47.

**Umbral de aceptación.** Con vectores de juguete en 2D, un score por encima de ~0.7 ya separa
bien "relevante" de "no relevante" (0.82 vs. 0.47 en el ejemplo). En los embeddings reales de
3072 dimensiones (A.4) los números no son directamente comparables a este ejemplo 2D — el
umbral real se calibra en C.2 con distancias observadas, no con esta demo. Si ninguna
coincidencia supera el umbral, el sistema no debe forzar el resultado más cercano: tiene que
responder que no tiene esa información (ver C.2).

## A.3 — `base_conocimiento.json`

16 documentos: **9 fichas de herramienta** (una por cada código canónico de `CATALOGO_ALIAS` en
`schemas.py` de la Entrega 1 — taladro, hidrolavadora, lijadora, amoladora, sierra_circular,
andamio, martillo_demoledor, hormigonera — más una segunda ficha de taladro **descontinuada**,
`activo: false`, que arma la Killer Query 2) y **7 documentos de política** (depósito de
garantía, requisitos de retiro, envío, cancelación, horarios, rotura en uso, seguridad).

Esquema de metadatos, siguiendo la Regla del Arquitecto (filtro duro → metadato, narrativo →
texto):

| Metadato | Tipo | Por qué es metadato y no texto |
|---|---|---|
| `categoria` | categórico | Se filtra con `$eq` (B.4); no hace falta leer el texto para saber la categoría. |
| `activo` | booleano | Es exactamente el filtro duro de la Killer Query 2: "solo herramientas vigentes". |
| `tipo_documento` | categórico | Separa fichas de herramienta de políticas — útil para acotar una búsqueda a un tipo. |
| `codigo_herramienta` | categórico (solo fichas) | Los mismos valores del `Literal` de `schemas.py` — el enganche con C.1: es el mismo código que el LLM de la Entrega 1 ya extrae del `texto_libre`. |
| `tags_regionales` | array de texto | Jerga y sinónimos — **no** es un filtro duro, es vocabulario adicional para la búsqueda semántica, por eso no se usa en ningún `where` de B.4. |

Lo narrativo (usos, para qué sirve, para qué no, consejos, jerga en prosa) queda **dentro** de
`descripcion_semantica`, nunca en metadatos — es lo que el modelo de embeddings necesita leer
para entender significado, no para filtrar.

## A.4 — `pipeline_vectorial.py`: índice FAISS

`IndexFlatIP` sobre vectores L2-normalizados (equivalente a similitud coseno), embeddings con
`gemini-embedding-001` (3072 dimensiones), persistido con `faiss.write_index()` y recargado con
`faiss.read_index()` si ya existe. 3 consultas de prueba corridas contra la API real:

```
Consulta: necesito algo para romper una pared de material
  score=0.7018  DOC-008 (martillo_demoledor)
  score=0.6569  DOC-001 (taladro)
  score=0.6238  DOC-002 (taladro, descontinuado)

Consulta: quiero alquilar algo para limpiar el frente de mi casa
  score=0.7063  DOC-003 (hidrolavadora)
  score=0.6601  DOC-012 (política de envío)
  score=0.6578  DOC-009 (hormigonera)

Consulta: cuanto tengo que dejar de seña si alquilo algo
  score=0.7582  DOC-010 (política de depósito)
  score=0.6761  DOC-011 (política de requisitos)
  score=0.6643  DOC-015 (política de rotura en uso)
```

(`score` acá es similitud coseno vía producto interno — más alto es más parecido; en B, con
ChromaDB, se reporta como distancia coseno, `1 - similitud`, más bajo es más parecido — la
misma matemática, presentada como espera cada herramienta.)

## A.5 — Prueba destructiva: volatilidad de la RAM

Se borró `faiss_index/` a mano (simulando el reinicio de un servidor) y se corrió el pipeline
dos veces seguidas. Log real, sin editar:

**Corrida 1 — sin índice persistido (el servidor "se reinició" y no había disco):**
```
[persistencia] No hay indice en disco: generando embeddings NUEVOS para 16 documentos (esto consume tokens de la API)...
[persistencia] Indice persistido en faiss_index\alquiherramientas.index (3072 dimensiones, 16 vectores) -- faiss.write_index()
```

**Corrida 2 — con el índice ya en disco (arranque siguiente):**
```
[persistencia] Indice encontrado en disco: cargando desde faiss_index\alquiherramientas.index (faiss.read_index, no se llama a la API de embeddings)
```

**Reflexión.** En producción, si el servidor se reinicia y el índice vive solo en RAM (nunca se
llamó a `write_index()`), hay que volver a pagar los embeddings de los 16 documentos antes de
poder responder la primera consulta — con un catálogo más grande, eso puede ser una ventana de
minutos sin servicio. Si hay dos servidores detrás de un balanceador y cada uno mantiene su
propio índice en RAM sin persistencia compartida, cada uno puede terminar con una versión
distinta de la base según cuándo arrancó — la razón de fondo por la que en la Parte B se migra a
ChromaDB con `PersistentClient`, que resuelve esto con una base real en disco en vez de un
archivo de índice suelto.

---

# Parte B — ChromaDB, Filtrado Híbrido y ETL

## B.1 — Migración a ChromaDB

`chromadb.PersistentClient(path="./chroma_db")`, colección `alquiherramientas` con
`metadata={"hnsw:space": "cosine"}`, `EmbeddingFunction` de Gemini (la misma familia de
embeddings que FAISS, `chromadb.utils.embedding_functions.GoogleGeminiEmbeddingFunction`).
Ingesta con `collection.upsert(...)` — correr `python vector_db.py --cargar` dos veces no
duplica nada, solo vuelve a escribir los mismos 16 documentos.

## B.2 — Los tres límites de FAISS que ChromaDB resuelve

| Límite de FAISS | Cómo se manifiesta en AlquiHerramientas | Cómo lo resuelve ChromaDB |
|---|---|---|
| Sin persistencia transaccional / atomicidad | `pipeline_vectorial.py` guarda el índice y el mapeo de ids en **dos archivos separados** (`alquiherramientas.index` + `ids.json`); si el proceso se corta entre los dos `write`, quedan desincronizados. | `PersistentClient` escribe en una base real (SQLite internamente) con las garantías transaccionales de una base de datos: documento, embedding y metadatos se guardan como una unidad. |
| Sin filtrado híbrido nativo | Para responder solo con herramientas activas, `pipeline_vectorial.py` tendría que traer el top-K y filtrar en Python **después** — exactamente el post-filtering que B.4 prohíbe, y que calcula similitud sobre candidatos que después se descartan. | `collection.query(..., where={...})` aplica el filtro **antes/durante** la búsqueda por similitud, con operadores nativos (`$eq`, `$and`). |
| CRUD ineficiente / sin concurrencia | Actualizar un solo documento (p. ej. marcar la sierra circular como inactiva, B.3) en FAISS obliga a reconstruir o reindexar manualmente qué posición del array corresponde a qué id. | `collection.upsert(ids=[...])` actualiza por id directamente, con la base pensada para escrituras concurrentes. |

## B.3 — Evento de negocio en caliente

`python vector_db.py --evento-en-caliente` (corrida real): la sierra circular (`DOC-006`) entra
a service y vuelve a estar disponible, verificado con `collection.get()` en cada paso:

```
Estado antes:  activo=True
Estado despues del upsert (rota, entra a service): activo=False
Estado despues de la reparacion: activo=True
```

**Por qué `upsert` y no `add`/`update`:** `add()` falla si el id ya existe (rompería la
re-ejecución idempotente de B.1); `update()` falla si el id todavía no existe. `upsert()` cubre
los dos casos con una sola llamada — exactamente lo que hace falta para un evento que puede ser
la primera vez que se toca ese documento o la enésima.

## B.4 — CLI de búsqueda híbrida

`buscar_alquiherramientas(query_semantica, categoria=None, tipo_documento=None,
codigo_herramienta=None, solo_activos=True, n_resultados=5)` en `vector_db.py`. El filtro se
arma como un `where` con `$and` de condiciones `$eq` — **nunca** hay un `if` de Python después
de la query descartando resultados; lo que Chroma calcula similitud sobre es exactamente lo que
el `where` ya redujo.

## B.5 — ETL y purga semántica

`etl_purga.py` simula un lote de 6 documentos que alguien intenta sumar "a mano" a la base:

1. **Normalización** (corrida real): `DOC-020` traía la clave `descripcion` en vez de
   `descripcion_semantica`; `DOC-021` traía `activo: "si"` (string) en vez de `true`. Ambos se
   corrigieron antes de seguir.
2. **Colisión de ID:** dos registros distintos usaban `DOC-019`. El segundo se reasignó a
   `DOC-900` (rango reservado para reasignaciones) sin pisar el primero.
3. **Purga semántica** — cada registro (ya normalizado) se comparó por distancia coseno contra
   los 16 documentos de `base_conocimiento.json`:

```
DOC-017 PURGADO: distancia 0.1920 a DOC-004 (lijadora)
DOC-018 PURGADO: distancia 0.1673 a DOC-003 (hidrolavadora)
DOC-019 CONSERVADO: distancia minima 0.3116 a DOC-005 (amoladora)
DOC-900 CONSERVADO: distancia minima 0.2807 a DOC-003 (hidrolavadora)
DOC-020 CONSERVADO: distancia minima 0.2739 a DOC-013 (politica)
DOC-021 CONSERVADO: distancia minima 0.2814 a DOC-010 (politica)

Resultado: 4/6 registros son contenido nuevo real. Purgados: 2.
```

**Umbral (0.22):** los dos casi-duplicados a propósito de este lote miden 0.1673 y 0.1920; el
contenido genuinamente nuevo arranca en 0.2739. Hay un salto claro de ~0.08 entre ambos grupos;
0.22 cae justo en el medio.

**Por qué un `SELECT DISTINCT` no lo habría encontrado:** ni los ids (`DOC-017`/`DOC-018` vs.
`DOC-004`/`DOC-003`) ni el texto coinciden — son paráfrasis con otra jerga ("lija eléctrica" en
vez de "lijadora orbital", "lavadora a presión" en vez de "hidrolavadora"). Un `DISTINCT` sobre
texto exacto los habría tratado como cuatro filas completamente distintas; la purga semántica los
reconoce como el mismo concepto porque compara significado, no strings.

## B.6 — Killer Queries

Tabla completa y corrida real en [`resultados_killer_queries.md`](resultados_killer_queries.md).
Resumen:

| # | Qué prueba | Resultado real | ¿Pasó? |
|---|---|---|---|
| 1 | Jerga sin palabras exactas del documento | `DOC-008` (martillo demoledor) primero, distancia 0.2896, pese a que "cascotes" y "embaldosar" no están en su texto | Sí |
| 2 | El metadato salva el día | Sin filtro, `DOC-002` (taladro descontinuado) queda en el top-2 a una distancia casi idéntica a `DOC-001` (0.2971 vs. 0.2910); con el `where` de `activo`, `DOC-002` desaparece por completo | Sí |
| 3 | Consulta fuera de catálogo ("generador eléctrico portátil") | Mejor distancia 0.3507, por encima del umbral de 0.32 → el sistema debe responder "no tengo eso" | Sí |

---

# Parte C — Coherencia e Informe

## C.1 — Cadena de coherencia con la Entrega 1

| Elemento de la Entrega 1 | Cómo se implementa en la Entrega 2 |
|---|---|
| Columna "Base de Conocimiento" del PEAS (A.3 de la Entrega 1: *"hoy no existe"*) | ← la colección ChromaDB `alquiherramientas` con estos 16 documentos |
| Campos de filtrado de la Matriz de Intenciones (B.3 de la Entrega 1) | ← los metadatos `categoria`, `activo`, `codigo_herramienta` de cada documento |
| `herramienta` que el LLM extraía del `texto_libre` (schemas.py, `CATALOGO_ALIAS`) | ← ahora es literalmente el mismo valor que llega como `codigo_herramienta` al `where` de `buscar_alquiherramientas()` |
| Límite de `CATALOGO_ALIAS` (diccionario estático, señalado en B.4 de la Entrega 1) | ← superado: `tags_regionales` + búsqueda semántica reconocen jerga que el diccionario nunca tenía cargada |

## C.2 — El umbral de aceptación

**0.32** de distancia coseno (Chroma), calibrado con las distancias reales observadas en B.6: los
mejores resultados genuinamente relevantes caen en 0.29–0.31; la consulta fuera de catálogo
("generador eléctrico portátil") cae en 0.3507, ya sobre el umbral. Es un umbral distinto al de
la purga de duplicados en B.5 (0.22) porque son preguntas distintas: B.5 pregunta *"¿es
literalmente el mismo documento?"* (debe ser muy estricto), C.2/B.6 pregunta *"¿es lo bastante
relevante para esta consulta?"* (puede ser más laxo).

Cuando ninguna distancia supera el umbral, el sistema **no** debe forzar el resultado más
cercano como respuesta — eso sería la misma alucinación de la Entrega 1 (A.2: el modelo que
afirmaba "tenemos disponibilidad" sin tener esa información), solo que ahora disfrazada de
"resultado de búsqueda". Lo correcto es responder que no se tiene esa información y, si
corresponde, escalar a un humano — el mismo criterio que ya aplica `requiere_humano` en el
pipeline de la Entrega 1.

## C.3 — Cierre: dónde se conecta

`buscar_alquiherramientas()` devuelve un `dict` de Python con ids, documentos, metadatos y
distancias — no una respuesta en lenguaje natural para el cliente. Lo que falta para cerrar el
ciclo es el **orquestador**: un componente que decida cuándo consultar la base vectorial (una
pregunta de contenido) versus el SQL de `db.py` de la Entrega 1 (una pregunta de stock, precio o
reserva), y que redacte la respuesta final combinando lo que corresponda de cada fuente. Eso es
exactamente RAG con LangChain (Unidad 4): la Entrega 2 deja lista la Base de Conocimiento que a
la Entrega 1 le faltaba: lo que sigue es el componente que la consulta en el momento justo.
