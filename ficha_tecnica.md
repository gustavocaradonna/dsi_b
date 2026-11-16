# Ficha técnica — Agente AlquiHerramientas

**Asignatura:** Desarrollo de Sistemas de Inteligencia Artificial (IADS 3) · **TP Final Integrador**
**Integrantes:** Joaquín Soriano · Gustavo Caradonna · Melina Kanesky · Nicolas Bovino · Patricio Joandet
**Versión:** 1.0.0 · **Repositorio:** https://github.com/gustavocaradonna/dsi_b

## 1. Qué es

Un asistente para el WhatsApp de **AlquiHerramientas**, un local de alquiler de herramientas. Responde
consultas sobre herramientas y políticas, informa stock y precios reales, y toma reservas. Es un
**agente ReAct** (LangGraph): en cada mensaje decide qué herramientas usar, en qué orden y cuándo
responder. Se expone como API REST.

| | |
|---|---|
| **Usuarios** | Clientes del local (por WhatsApp; la API es el backend del canal) |
| **Problema que resuelve** | Las consultas repetitivas (stock, precio, requisitos, horarios) y la toma de reservas sin intervención humana, sin inventar datos (la alucinación documentada en la Entrega 1, A.2) |
| **Fuera de alcance** | Pagos, confirmación final de reservas (quedan `pendiente`), consultas ajenas al alquiler |

## 2. Arquitectura

```
cliente ─► POST /consultar ─► guardrails de entrada ─► agente ReAct (LangGraph) ─► guardrail de salida ─► respuesta
                                  (longitud,               │   ▲                      (enmascarado de
                                   prompt injection)       ▼   │                       datos personales)
                                                       herramientas      memoria SQLite por thread_id
                                     ┌──────────────┬──────────────┬──────────────┐
                                     │ buscar_      │ consultar_   │ crear_       │
                                     │ informacion  │ disponibilidad│ reserva     │
                                     │ (RAG E3)     │ consultar_   │ (actuador)   │
                                     │              │ precio       │              │
                                     │              │ (sensores)   │              │
                                     ▼              ▼              ▼
                              ChromaDB (E2/E3)   SQLite de negocio (E1: catálogo, stock, reservas)
```

| Componente | Tecnología | Archivo |
|---|---|---|
| Orquestación del agente | LangGraph 1.2 — `StateGraph` ReAct explícito | `agente.py` |
| LLM (agente, juez de relevancia) | Gemini `gemini-3.5-flash-lite` vía `langchain-google-genai` | `agente.py`, `entrega_3/rag_pipeline.py` |
| Embeddings | `gemini-embedding-001` (3072 dimensiones) | `vector_db.py` |
| Base vectorial | ChromaDB persistente: colección `alquiherramientas` (16 docs) y `alquiherramientas_chunks` (26 chunks, 500/100) | `vector_db.py`, `entrega_3/rag_pipeline.py` |
| Datos de negocio | SQLite: catálogo, stock, precios, clientes, reservas | `db.py` |
| Memoria conversacional | `SqliteSaver` (langgraph-checkpoint-sqlite), archivo `memoria_agente.sqlite` | `agente.py` |
| API | FastAPI + uvicorn | `api.py` |
| Observabilidad | Logs JSON (`logs/agente.jsonl`), `/metricas`, LangSmith | `observabilidad.py` |
| Seguridad | Validadores deterministas (regex) + reglas del prompt + validaciones del actuador | `guardrails.py`, `agente.py` |

## 3. Herramientas del agente

| Herramienta | Tipo | Entrada | Salida | Efecto |
|---|---|---|---|---|
| `buscar_informacion` | Retriever (RAG de la E3) | consulta en lenguaje natural | documentos con id `[DOC-xxx]`, metadatos y texto completo, o `SIN_RESULTADOS` | Solo lectura. Chunks k=8 → juez LLM (puntaje ≥ 6) → documento padre |
| `consultar_disponibilidad` | **Sensor** | herramienta, fecha_inicio, fecha_fin, cantidad | stock total, disponibles, disponible (bool), precio por día | Solo lectura (SQL) |
| `consultar_precio` | **Sensor** | herramienta, días | precio por día, total y depósito | Solo lectura (SQL). El total lo calcula el código |
| `crear_reserva` | **Actuador** | herramienta, fechas, teléfono, cantidad | reserva_id, estado `pendiente`, total, depósito; o motivo del rechazo | **Escribe** en SQL y ocupa stock. Valida fechas (no pasadas, máx. 30 días), cantidad (1–10), teléfono (8–15 dígitos) y stock real antes de escribir |

Todas tienen docstring completo: qué hacen, cuándo usarlas y cuándo **no**, argumentos y retorno. Es
lo que el modelo lee para decidir.

## 4. Decisiones de diseño

| Decisión | Por qué |
|---|---|
| Grafo ReAct propio (no `create_react_agent`) | El límite de iteraciones queda visible y testeable: contador por turno + nodo `limite` con mensaje fijo, y `recursion_limit` como segunda barrera |
| `MAX_ITERACIONES = 5` rondas por mensaje | La consulta más compleja medida usó 1 ronda (las herramientas se piden en paralelo). 5 deja margen para preguntas multi-parte sin permitir loops caros |
| La descomposición de consulta de la E3 la hace el loop ReAct | El prompt pide una llamada a `buscar_informacion` por cada parte de la pregunta: la mejora que la E3 midió para C4, sin un LLM extra fijo por mensaje |
| Precios y stock solo desde SQL | El RAG no tiene precios a propósito (E3, regla de guardrail). Un dato numérico siempre sale de una consulta verificable |
| Guardrails deterministas (regex) | Primera línea barata y testeable con asserts exactos. Un mensaje bloqueado no gasta tokens |
| Memoria en SQLite, separada de la base de negocio | Sobrevive reinicios (es un archivo) y no mezcla conversación con datos transaccionales |
| Rutas resueltas respecto del repo | La API funciona igual sin importar desde qué directorio se lanza |
| Bases que se construyen solas en el primer arranque | `chroma_db/` y las bases SQLite son derivados (`.gitignore`). En otra máquina, `uvicorn api:app` alcanza |

## 5. API

| Endpoint | Descripción | Códigos |
|---|---|---|
| `GET /health` | Estado del servicio, archivo de memoria y límite de iteraciones | 200 |
| `POST /consultar` | `{"mensaje", "thread_id"?}` → respuesta, herramientas usadas, iteraciones, corte por límite, datos enmascarados, latencia, tokens y costo | 200, 400 (bloqueo de guardrail), 422 (cuerpo inválido), 500 |
| `GET /estado/{thread_id}` | Historial de la conversación desde la memoria (con datos personales enmascarados) | 200, 404 |
| `GET /metricas` | Consultas, respondidas, errores, bloqueos por motivo, latencia promedio y p95, uso de herramientas, tokens y costo | 200 |

## 6. Seguridad

| Capa | Control | Dónde |
|---|---|---|
| Entrada | Longitud: vacío o más de 1.000 caracteres → 400 | `guardrails.validar_longitud` |
| Entrada | Prompt injection: 6 tácticas (pisar instrucciones, extraer el prompt, cambio de rol, jailbreak, etiquetas de rol), sin falsos positivos con "instrucciones de uso", "reglas de cancelación", etc. | `guardrails.validar_prompt_injection` |
| Salida | Enmascarado de DNI, teléfono, email y tarjeta (Luhn) en la respuesta y en `/estado`; no toca fechas, montos ni porcentajes | `guardrails.enmascarar_datos_personales` |
| Prompt | Solo datos de herramientas; no confirmar lo que el cliente afirma sin respaldo; frase de escape; ignorar instrucciones contrarias | `agente.PROMPT_SISTEMA` |
| Actuador | Validación de fechas, cantidad, teléfono y stock real dentro de la herramienta, no en el prompt | `agente.crear_reserva` |
| Datos | `.env`, memoria, logs y bases fuera del repo (`.gitignore`); los logs guardan el largo del mensaje y la versión enmascarada, nunca el texto crudo | `.gitignore`, `api.py` |

**Suite automática:** `security_tests.py` corre **27 casos (13 tests) en ~3 s, sin API key**. Detectó
dos bugs reales durante el desarrollo: un teléfono y una tarjeta al final de una oración quedaban
sin enmascarar por el punto final.

**Entrada HTTP:** cuerpos de más de 64 KB → 413. Los cuerpos en cp1252 (los que manda `curl` en
Windows) se normalizan a UTF-8, y todas las respuestas declaran `charset=utf-8`. Los dos problemas se
detectaron siguiendo el README en un clon limpio.

## 7. Resultados medidos

| Qué | Resultado | Evidencia |
|---|---|---|
| Matriz de validación del agente (4 escenarios, chequeos automáticos) | **4/4** | `tp_final/resultados_matriz.md` |
| Instalación en máquina limpia siguiendo solo el README | OK: clon nuevo, entorno virtual nuevo, primer arranque construye las bases solo (26 s) | `informe.md`, TP Final B.3 |
| Memoria vía HTTP después de reiniciar el proceso | Sí: el segundo turno ("¿y cuánto me sale por ese día?") se resuelve con lo dicho antes del reinicio | `tp_final/evidencia_api_http.md` |
| Tests de seguridad | **27/27** | `security_tests.py` |
| Tokens por consulta (promedio / p95) | 4.566 / 6.530 | `tp_final/analisis_costos.md` |
| Costo por consulta (promedio) | USD 0.0019 (≈ USD 168/mes a 3.000 consultas/día) | `tp_final/analisis_costos.md` |
| Latencia (p50 / p95) | 10.0 s / 35.4 s (free tier de Gemini, incluye un arranque en frío) | `tp_final/analisis_costos.md` |
| Calidad del retrieval (E3, golden dataset, juez `gemini-3.1-flash-lite`) | Context Recall por IDs 1.000, Answer Relevancy 0.736 | `entrega_3/resultados_ragas.md` |

## 8. Límites conocidos y riesgos

| Límite | Impacto | Mitigación propuesta |
|---|---|---|
| ~2.000 tokens fijos por llamada al agente (prompt + 4 herramientas) | El 92 % de los tokens es del agente, no del RAG | Caché de contexto del proveedor para el prefijo fijo; acortar docstrings sin perder el "cuándo NO usarla" |
| Latencia p95 alta en el free tier | Respuestas de 10–35 s | Plan pago (menos reintentos 429/503) y streaming de la respuesta |
| Guardrail de injection por regex | Un ataque reformulado puede pasar | Lo frena la segunda capa (prompt + herramientas que solo devuelven datos verificados). Próximo paso: clasificador LLM para los casos que la regex no cubre |
| Métricas en memoria del proceso | Se reinician con el servidor | El histórico queda en `logs/agente.jsonl`; en producción, exportar a Prometheus |
| Una sola instancia (SQLite) | No escala horizontalmente | Memoria y negocio a Postgres (`sql/schema.sql` ya existe) y checkpointer de LangGraph para Postgres |
| Las reservas quedan `pendiente` | Requiere confirmación humana | Es una decisión de negocio: el agente no cobra ni confirma |
| Gemini 3.5 ignora `temperature=0` | Respuestas no deterministas | La varianza de selección del juez se midió (E3, B.4): misma selección en 15/15 repeticiones |

## 9. Operación

| Variable | Default | Para qué |
|---|---|---|
| `GEMINI_API_KEY` | — (obligatoria) | LLM y embeddings |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Modelo del agente y del juez |
| `MAX_ITERACIONES` | `5` | Rondas agente → herramientas por mensaje |
| `RUTA_MEMORIA` | `memoria_agente.sqlite` | Memoria del agente (relativa al repo) |
| `PRECIO_ENTRADA_USD_1M` / `PRECIO_SALIDA_USD_1M` | `0.30` / `2.50` | Costo estimado en `/metricas` |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | `true` / — / — | Trazas (opcional) |

Levantar: `pip install -r requirements.txt` → completar `.env` → `uvicorn api:app --port 8000` (ver README).
