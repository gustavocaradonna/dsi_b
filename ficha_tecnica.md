# Ficha técnica — Agente AlquiHerramientas

**Asignatura:** Desarrollo de Sistemas de Inteligencia Artificial (IADS 3) · **TP Final Integrador**
**Integrantes:** Joaquín Soriano · Gustavo Caradonna · Melina Kanesky · Nicolas Bovino · Patricio Joandet
**Versión:** 2.0.0 (reorganizada con Vertical Slice Architecture) · **Repositorio:** https://github.com/gustavocaradonna/dsi_b

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
cliente ─► app/features/consultar ─► shared/guardrails (entrada) ─► app/agente (ReAct) ─► shared/guardrails (salida) ─► respuesta
                                       (longitud,                       │   ▲                (enmascarado de
                                        prompt injection)               ▼   │                 datos personales)
                                                             app/herramientas/*     memoria SQLite por thread_id
                                     ┌─────────────────┬──────────────────┬───────────────┬──────────────┐
                                     │ conocimiento/   │ disponibilidad/  │ precio/       │ reservas/    │
                                     │ buscar_         │ consultar_       │ consultar_    │ crear_       │
                                     │ informacion     │ disponibilidad   │ precio        │ reserva      │
                                     │ (RAG E3)        │ (sensor)         │ (sensor)      │ (actuador)   │
                                     ▼                 ▼                  ▼               ▼
                              ChromaDB (data/chroma_db)   SQLite de negocio (data/alquiherramientas.db)
```

| Componente | Tecnología | Dónde |
|---|---|---|
| Composición de la API | FastAPI: registra un router por slice | `app/main.py` |
| Casos de uso HTTP | Un slice por endpoint: consultar, estado, metricas, health | `app/features/<slice>/` |
| Herramientas del agente | Un slice por capacidad, con su tool y su acceso a datos | `app/herramientas/<slice>/` |
| Orquestación del agente | LangGraph 1.2 — `StateGraph` ReAct explícito | `app/agente/grafo.py` |
| LLM (agente, juez de relevancia) | Gemini `gemini-3.5-flash-lite` vía `langchain-google-genai` | `app/shared/llm.py` |
| Embeddings y base vectorial | `gemini-embedding-001` (3072 dimensiones) · ChromaDB, colección `alquiherramientas_chunks` (26 chunks, 500/100) | `app/herramientas/conocimiento/indice.py` |
| Datos de negocio | SQLite: catálogo, stock, precios, clientes, reservas | `app/shared/sql.py` (conexión y esquema) + `consultas.py` de cada slice |
| Memoria conversacional | `SqliteSaver` (langgraph-checkpoint-sqlite), archivo `data/memoria_agente.sqlite` | `app/agente/memoria.py` |
| Observabilidad | Logs JSON (`data/logs/agente.jsonl`), `/metricas`, LangSmith | `app/shared/observabilidad.py` |
| Seguridad | Validadores deterministas (regex) + reglas del prompt + validaciones del actuador | `app/shared/guardrails.py`, `app/herramientas/reservas/` |
| Configuración | Rutas y variables de entorno en un solo lugar | `app/shared/config.py` |
| Despliegue | Docker: imagen multi-stage (etapa `test` + `produccion`, Python 3.12 slim, usuario sin privilegios, healthcheck) + Compose con volumen para los datos | `Dockerfile`, `docker-compose.yml`, `requirements-app.txt` |

**Organización: Vertical Slice Architecture.** El código está cortado por funcionalidad, no por capa
técnica: cada caso de uso (endpoint o herramienta del agente) es una carpeta con todo lo que necesita,
y lo realmente transversal vive en `app/shared/`. Ningún slice importa a otro, y
`tests/test_arquitectura.py` lo verifica en cada corrida. El detalle está en la sección "Organización
del código" del TP Final en `informe.md`.

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
| Rutas resueltas respecto del repo, datos en `data/` | La API funciona igual sin importar desde qué directorio se lanza. Todo lo generado (bases, memoria, logs) está en una sola carpeta, configurable con `DIR_DATOS` |
| Vertical Slice Architecture | Un cambio de funcionalidad toca una sola carpeta. Las reglas de dependencias son tests, no convenciones |
| Bases que se construyen solas en el primer arranque | `data/` es derivado (`.gitignore`). En otra máquina, `uvicorn app.main:app` alcanza |

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
| Datos | `.env`, memoria, logs y bases fuera del repo (`.gitignore`); los logs guardan el largo del mensaje y la versión enmascarada, nunca el texto crudo | `.gitignore`, `app/features/consultar/handler.py` |

**Suite automática:** `tests/security_tests.py` corre **27 casos (13 tests) en ~3 s, sin API key**, y `tests/test_arquitectura.py` suma 101 chequeos de las reglas de los slices (128/128). Detectó
dos bugs reales durante el desarrollo: un teléfono y una tarjeta al final de una oración quedaban
sin enmascarar por el punto final.

**Entrada HTTP:** cuerpos de más de 64 KB → 413. Los cuerpos en cp1252 (los que manda `curl` en
Windows) se normalizan a UTF-8, y todas las respuestas declaran `charset=utf-8`. Los dos problemas se
detectaron siguiendo el README en un clon limpio.

## 7. Resultados medidos

| Qué | Resultado | Evidencia |
|---|---|---|
| Matriz de validación del agente (4 escenarios, chequeos automáticos) | **4/4** | `evidencia/resultados_matriz.md` |
| Instalación en máquina limpia siguiendo solo el README | OK: clon nuevo, entorno virtual nuevo, primer arranque construye las bases solo (26 s) | `informe.md`, TP Final B.3 |
| Memoria vía HTTP después de reiniciar el proceso | Sí: el segundo turno ("¿y cuánto me sale por ese día?") se resuelve con lo dicho antes del reinicio | `evidencia/evidencia_api_http.md` |
| Tests de seguridad · reglas de arquitectura | **27/27** · **101/101** | `tests/` |
| Tokens por consulta (promedio / p95) | 4.566 / 6.530 | `evidencia/analisis_costos.md` |
| Costo por consulta (promedio) | USD 0.0019 (≈ USD 168/mes a 3.000 consultas/día) | `evidencia/analisis_costos.md` |
| Latencia (p50 / p95) | 10.0 s / 35.4 s (free tier de Gemini, incluye un arranque en frío) | `evidencia/analisis_costos.md` |
| Calidad del retrieval (E3, golden dataset, juez `gemini-3.1-flash-lite`) | Context Recall por IDs 1.000, Answer Relevancy 0.736 | `entrega_3/resultados_ragas.md` |

## 8. Límites conocidos y riesgos

| Límite | Impacto | Mitigación propuesta |
|---|---|---|
| ~2.000 tokens fijos por llamada al agente (prompt + 4 herramientas) | El 92 % de los tokens es del agente, no del RAG | Caché de contexto del proveedor para el prefijo fijo; acortar docstrings sin perder el "cuándo NO usarla" |
| Latencia p95 alta en el free tier | Respuestas de 10–35 s | Plan pago (menos reintentos 429/503) y streaming de la respuesta |
| Guardrail de injection por regex | Un ataque reformulado puede pasar | Lo frena la segunda capa (prompt + herramientas que solo devuelven datos verificados). Próximo paso: clasificador LLM para los casos que la regex no cubre |
| Métricas en memoria del proceso | Se reinician con el servidor | El histórico queda en `data/logs/agente.jsonl`; en producción, exportar a Prometheus |
| Imagen de Docker de 667 MB | Casi todo es ChromaDB (trae `onnxruntime`) | Cliente HTTP de Chroma con un servidor de Chroma aparte en el mismo Compose |
| Una sola instancia (SQLite) | No escala horizontalmente | Memoria y negocio a Postgres (`sql/schema.sql` ya existe) y checkpointer de LangGraph para Postgres |
| Las reservas quedan `pendiente` | Requiere confirmación humana | Es una decisión de negocio: el agente no cobra ni confirma |
| Gemini 3.5 ignora `temperature=0` | Respuestas no deterministas | La varianza de selección del juez se midió (E3, B.4): misma selección en 15/15 repeticiones |

## 9. Operación

| Variable | Default | Para qué |
|---|---|---|
| `GEMINI_API_KEY` | — (obligatoria) | LLM y embeddings |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Modelo del agente y del juez |
| `MAX_ITERACIONES` | `5` | Rondas agente → herramientas por mensaje |
| `DIR_DATOS` | `data` | Carpeta de los datos generados (relativa al repo) |
| `RUTA_MEMORIA` | `memoria_agente.sqlite` | Memoria del agente, dentro de `DIR_DATOS` |
| `PRECIO_ENTRADA_USD_1M` / `PRECIO_SALIDA_USD_1M` | `0.30` / `2.50` | Costo estimado en `/metricas` |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | `true` / — / — | Trazas (opcional) |

Levantar con Docker: completar `.env` → `docker compose up --build` (la API queda en el puerto 8000; los datos, en el volumen
`alquiherramientas-datos`). Sin Docker: `pip install -r requirements.txt` → completar `.env` →
`uvicorn app.main:app --port 8000`. Detalle en el README.
