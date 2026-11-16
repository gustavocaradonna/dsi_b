# Entregas anteriores (archivo histórico)

Cada entrega quedó **tal como se entregó**, en su propia carpeta. Lo único que cambió al archivarlas
fueron las rutas para encontrar el `.env` de la raíz y, en la E3, el `vector_db.py` de la E2. El
sistema en producción del TP Final está en [`../app/`](../app/) y **no depende de esta carpeta**: lo
que usa de estas entregas lo tiene incorporado en sus slices (lo verifica
`tests/test_arquitectura.py`).

| Entrega | Carpeta | Informe | Tema |
|---|---|---|---|
| 1 | [`entrega_1/`](entrega_1/) | [`../informe.md`](../informe.md) (primera parte) | Extracción validada con Pydantic + SQL real |
| 2 | [`entrega_2/`](entrega_2/) | [`entrega_2/informe_entrega2.md`](entrega_2/informe_entrega2.md) | Base de conocimiento vectorial (FAISS + ChromaDB) |
| 3 | [`entrega_3/`](entrega_3/) | [`entrega_3/informe.md`](entrega_3/informe.md) | RAG con LangChain LCEL, chunking, reranking y RAGAS |

Instalación y `.env`: los mismos del sistema (ver el [README principal](../README.md)).

## Entrega 1 — Extracción validada

| Archivo | Contenido |
|---|---|
| [`entrega_1/schemas.py`](entrega_1/schemas.py) | Contrato Pydantic V2 (C.1): `Literal` de intenciones + validadores |
| [`entrega_1/app.py`](entrega_1/app.py) | Pipeline completo: extracción, contrato, SQL y redacción (C.2, C.3) |
| [`entrega_1/db.py`](entrega_1/db.py) | Capa SQL real (SQLite) — pasos 3 y 4 del flujo de B.6 |
| [`entrega_1/resultados_lote.md`](entrega_1/resultados_lote.md) | Tabla de resultados de los 6 casos (C.3) |
| [`entrega_1/resultados_zeroshot.md`](entrega_1/resultados_zeroshot.md) | El mismo lote sin ejemplos few-shot (C.4) |
| [`entrega_1/anatomia_token.py`](entrega_1/anatomia_token.py) | Análisis de tokens ES vs EN y costo del prompt (A.4) |
| [`entrega_1/evidencia_alucinacion.py`](entrega_1/evidencia_alucinacion.py) | Réplica de "El Proveedor Enojado" (A.2) |
| [`entrega_1/sql/schema.sql`](entrega_1/sql/schema.sql) | Esquema de base de datos (B.5.b, Postgres) |

Se corre **desde su carpeta** (usa rutas relativas al directorio de trabajo):

```bash
cd entregas/entrega_1
python app.py --md resultados_lote.md                      # lote de 6 casos
python app.py --texto "Hola, tenes hidrolavadora para el sabado?"
python app.py --zero-shot --md resultados_zeroshot.md      # sin few-shot (C.4)
python anatomia_token.py                                   # no necesita API key
python evidencia_alucinacion.py
```

## Entrega 2 — Base de conocimiento vectorial

| Archivo | Contenido |
|---|---|
| [`entrega_2/informe_entrega2.md`](entrega_2/informe_entrega2.md) | Informe de la Entrega 2 |
| [`entrega_2/base_conocimiento.json`](entrega_2/base_conocimiento.json) | Los 16 documentos tal como se entregaron (la copia vigente vive en `app/herramientas/conocimiento/`) |
| [`entrega_2/pipeline_vectorial.py`](entrega_2/pipeline_vectorial.py) | Índice FAISS persistido + similitud coseno a mano (A.2, A.4, A.5) |
| [`entrega_2/vector_db.py`](entrega_2/vector_db.py) | ChromaDB persistente, búsqueda híbrida, evento en caliente y Killer Queries (B.1–B.6) |
| [`entrega_2/etl_purga.py`](entrega_2/etl_purga.py) | ETL y purga semántica de un lote sucio (B.5) |
| [`entrega_2/resultados_killer_queries.md`](entrega_2/resultados_killer_queries.md) | Tabla de resultados de B.6 |

Se corre **desde su carpeta**:

```bash
cd entregas/entrega_2
python pipeline_vectorial.py                  # índice FAISS + 3 consultas (A.4)
python pipeline_vectorial.py --cosine-a-mano  # sin API (A.2)
python vector_db.py --cargar
python vector_db.py --buscar "necesito algo para romper una pared" --categoria electrico
python vector_db.py --evento-en-caliente      # B.3
python vector_db.py --killer-queries          # B.6
python etl_purga.py                           # B.5
```

`faiss_index/` y `chroma_db/` de esta entrega se crean dentro de `entrega_2/` y están en `.gitignore`.

## Entrega 3 — RAG con evaluación

| Archivo | Contenido |
|---|---|
| [`entrega_3/informe.md`](entrega_3/informe.md) | Informe analítico: falla del RAG básico, RAGAS y diagnóstico |
| [`entrega_3/rag_pipeline.py`](entrega_3/rag_pipeline.py) | Chain LCEL, chunking 500/100, reranking con juez LLM, traza, v2 de C.4 |
| [`entrega_3/evaluacion_ragas.py`](entrega_3/evaluacion_ragas.py) | Evaluación RAGAS sobre el golden dataset y el set held-out |
| [`entrega_3/golden_dataset.json`](entrega_3/golden_dataset.json) | 13 preguntas con ground truth y caso de prueba |
| [`entrega_3/calibracion_umbral.py`](entrega_3/calibracion_umbral.py) | Corrección de la E2: umbral recalibrado con validación held-out |
| [`entrega_3/varianza_jueces.py`](entrega_3/varianza_jueces.py) | Varianza de los jueces LLM entre corridas repetidas |
| [`entrega_3/langsmith_trace.png`](entrega_3/langsmith_trace.png) | Captura de la traza en LangSmith (B.4) |

Se puede correr **desde la raíz del repo**:

```bash
python entregas/entrega_3/rag_pipeline.py --reindexar
python entregas/entrega_3/rag_pipeline.py --matriz
python entregas/entrega_3/rag_pipeline.py --pregunta "..." --v2
python entregas/entrega_3/evaluacion_ragas.py --pipelines basico avanzado avanzado_v2 --evaluar-solo avanzado_v2
python entregas/entrega_3/varianza_jueces.py --reranker 5 --ragas 2
```

La E3 usa la colección ChromaDB de la E2 (`entregas/entrega_2/chroma_db`), que se reconstruye con
`python vector_db.py --cargar` desde `entregas/entrega_2/`.
