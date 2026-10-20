# AlquiHerramientas — TP Integrador (Entregas 1, 2 y 3)

Pipeline de extracción validada para el asistente de WhatsApp de **AlquiHerramientas**, un local
ficticio de alquiler de herramientas. Convierte mensajes de texto libre en datos estructurados
que cumplen un contrato, consulta el SQL real para stock/precio/reservas (Entrega 1), y desde la
Entrega 2 tiene además una Base de Conocimiento vectorial (FAISS + ChromaDB) para las preguntas
de contenido que ni el SQL ni el `CATALOGO_ALIAS` resuelven. La Entrega 3 monta encima un
pipeline RAG con LangChain LCEL (guardrails, chunking, reranking con LLM como juez) y lo evalúa
con RAGAS.

**Asignatura:** Desarrollo de Sistemas de Inteligencia Artificial

**Integrantes:**

- Joaquín Soriano
- Gustavo Caradonna
- Melina Kanesky
- Nicolas Bovino
- Patricio Joandet


---

## Qué hay acá

| Archivo | Contenido |
|---|---|
| [`informe.md`](informe.md) | Partes A y B completas + narrativa de C.4 y C.5 |
| [`schemas.py`](schemas.py) | Contrato Pydantic V2 (C.1): `Literal` de intenciones + validadores |
| [`app.py`](app.py) | Pipeline completo: extracción, contrato, SQL y redacción (C.2, C.3) |
| [`db.py`](db.py) | Capa SQL real (SQLite) — pasos 3 y 4 del flujo de B.6 |
| [`resultados_lote.md`](resultados_lote.md) | Tabla de resultados de los 6 casos (C.3) |
| [`anatomia_token.py`](anatomia_token.py) | Análisis de tokens ES vs EN y costo del prompt (A.4) |
| [`evidencia_alucinacion.py`](evidencia_alucinacion.py) | Réplica de "El Proveedor Enojado" (A.2) |
| [`sql/schema.sql`](sql/schema.sql) | Esquema de base de datos (B.5.b, Postgres) |
| [`.env.example`](.env.example) | Variables de entorno, sin valores reales |

**Entrega 2 — Base de Conocimiento Vectorial:**

| Archivo | Contenido |
|---|---|
| [`informe_entrega2.md`](informe_entrega2.md) | Partes A, B y C completas de la Entrega 2 |
| [`base_conocimiento.json`](base_conocimiento.json) | 16 documentos — la fuente de verdad de la Base de Conocimiento (A.3) |
| [`pipeline_vectorial.py`](pipeline_vectorial.py) | Índice FAISS persistido + similitud coseno a mano (A.2, A.4, A.5) |
| [`vector_db.py`](vector_db.py) | ChromaDB persistente, búsqueda híbrida, evento en caliente y Killer Queries (B.1–B.6) |
| [`etl_purga.py`](etl_purga.py) | ETL y purga semántica de un lote sucio (B.5) |
| [`resultados_killer_queries.md`](resultados_killer_queries.md) | Tabla de resultados de B.6 |

**Entrega 3 — Sistema RAG con evaluación** (carpeta [`entrega_3/`](entrega_3/)):

| Archivo | Contenido |
|---|---|
| [`entrega_3/informe.md`](entrega_3/informe.md) | Informe analítico: falla del RAG básico, tabla comparativa RAGAS y diagnóstico |
| [`entrega_3/rag_pipeline.py`](entrega_3/rag_pipeline.py) | Partes A y B: chain LCEL sobre la ChromaDB de la Entrega 2, chunking 500/100, reranking con juez LLM, traza |
| [`entrega_3/evaluacion_ragas.py`](entrega_3/evaluacion_ragas.py) | Parte C: corre los pipelines sobre el golden dataset y evalúa con RAGAS |
| [`entrega_3/golden_dataset.json`](entrega_3/golden_dataset.json) | 10 preguntas con ground truth (se reusa en las Entregas 4 y 5) |
| [`entrega_3/calibracion_umbral.py`](entrega_3/calibracion_umbral.py) | Corrección de la Entrega 2: recalibración del umbral con 40 consultas y validación held-out |
| [`entrega_3/resultados_pipeline.md`](entrega_3/resultados_pipeline.md) | Salidas reales de A.3, A.4, B.1–B.4 |
| [`entrega_3/resultados_ragas.md`](entrega_3/resultados_ragas.md) | Métricas RAGAS completas, por tipo y por pregunta |
| [`entrega_3/langsmith_trace.png`](entrega_3/langsmith_trace.png) | Captura de la traza en LangSmith (B.4) |

## Requisitos

- Python 3.10 o superior
- Una API key de Google AI Studio: https://aistudio.google.com/apikey (tiene free tier)

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración

Copiar `.env.example` a `.env` y completar la key:

```bash
cp .env.example .env
```

| Variable | Descripción | Default |
|---|---|---|
| `GEMINI_API_KEY` | API key de Google AI Studio. **Obligatoria.** | — |
| `GEMINI_MODEL` | Modelo a usar | `gemini-3.5-flash-lite` |
| `GEMINI_TEMPERATURE` | Temperatura de extracción | `0` |
| `GEMINI_EMBEDDING_MODEL` | Modelo de embeddings (Entrega 2) | `gemini-embedding-001` |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | Trazas en LangSmith (Entrega 3) | `true` / — / `alquiherramientas-entrega3` |
| `RAGAS_LLM_MODEL` | Modelo juez de RAGAS (Entrega 3) | el de `GEMINI_MODEL` |

> **`.env` está en `.gitignore` desde el primer commit y nunca se sube.** Si alguna vez se
> filtra una key, no alcanza con borrarla: hay que **rotarla** en AI Studio.

No hace falta levantar Postgres para correr el pipeline: `app.py` inicializa
`alquiherramientas.db` (SQLite, vía `db.py`) automáticamente en la primera corrida, con el
catálogo de herramientas ya sembrado. Ese archivo es un binario derivado — está en
`.gitignore`, no se commitea, se reconstruye solo.

## Uso

Correr el lote de prueba de 6 casos y regenerar la tabla de resultados:

```bash
python app.py --md resultados_lote.md
```

Procesar un solo mensaje:

```bash
python app.py --texto "Hola, tenes hidrolavadora para el sabado?"
```

Correr el lote sin ejemplos few-shot, para comparar técnicas de prompting (C.4):

```bash
python app.py --zero-shot --md resultados_zeroshot.md
```

Análisis de tokens (no necesita API key):

```bash
python anatomia_token.py
```

Generar la evidencia de alucinación de la Parte A.2:

```bash
python evidencia_alucinacion.py
```

**Entrega 2 — Base de Conocimiento Vectorial:**

Construir/recargar el índice FAISS y correr las 3 consultas de prueba (A.4):

```bash
python pipeline_vectorial.py
```

Calculo de similitud coseno a mano, sin llamar a la API (A.2):

```bash
python pipeline_vectorial.py --cosine-a-mano
```

Cargar (o recargar) la colección de ChromaDB y hacer una búsqueda híbrida ad-hoc:

```bash
python vector_db.py --cargar
python vector_db.py --buscar "necesito algo para romper una pared" --categoria electrico
```

Demo del evento en caliente (B.3) y de las Killer Queries (B.6):

```bash
python vector_db.py --evento-en-caliente
python vector_db.py --killer-queries
```

Correr el ETL y la purga semántica sobre el lote sucio de prueba (B.5):

```bash
python etl_purga.py
```

**Entrega 3 — RAG + RAGAS** (completar `LANGSMITH_*` en `.env` para trazar en LangSmith):

```bash
py entrega_3/calibracion_umbral.py                # recalibra el umbral de vector_db.py (correccion E2)
py entrega_3/rag_pipeline.py --reindexar          # B.2: coleccion de chunks 500/100
py entrega_3/rag_pipeline.py --matriz             # A.3 y A.4
py entrega_3/rag_pipeline.py --falla              # B.1-B.3: basico vs solo chunking vs avanzado
py entrega_3/rag_pipeline.py --traza              # B.4: corrida instrumentada (y traza en LangSmith)
py entrega_3/rag_pipeline.py --pregunta "..." --avanzado
py entrega_3/evaluacion_ragas.py --pipelines basico solo_chunks avanzado
```

`faiss_index/` y `chroma_db/` son binarios derivados (igual que `alquiherramientas.db`): están
en `.gitignore` y se reconstruyen enteros desde `base_conocimiento.json`.

## Cómo funciona

```
Mensaje de WhatsApp (texto libre)
   │
   ├─ [LLM]      Gemini + Structured Outputs  ──► JSON con la forma esperada
   │
   ├─ [Pydantic] Valida las reglas de negocio ──► acepta … o RECHAZA
   │                                              (herramienta fuera de catálogo,
   │                                               reserva sin fecha, confianza baja)
   │
   ├─ [SQL]      db.py consulta stock/precio reales o crea la reserva `pendiente`
   │
   ├─ [LLM]      redacta la respuesta final SOLO sobre esos datos verificados
   │              (fuera_de_alcance / requiere_humano: mensaje fijo, sin gastar LLM)
   │
   └─ Salida: SolicitudAlquiler validada + resultado de SQL + respuesta lista para enviar
```

El JSON Schema que se le pasa a Gemini es **deliberadamente más permisivo** que el modelo
Pydantic: el LLM garantiza la *forma*, Pydantic garantiza las *reglas de negocio*. Si fueran
idénticos nunca se podría observar un `ValidationError` — y esa aduana es el punto del TP.

Las cuatro intenciones (`consultar_disponibilidad`, `consultar_precio`, `solicitar_reserva`,
`fuera_de_alcance`) son las mismas en la Matriz de Intenciones del informe, en el `Literal` de
`schemas.py`, en el System Prompt y en la tabla de resultados.
