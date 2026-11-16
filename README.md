# AlquiHerramientas — TP Integrador (IADS 3)

Asistente de WhatsApp para **AlquiHerramientas**, un local ficticio de alquiler de herramientas. El
sistema final es un **agente ReAct con LangGraph**: decide solo qué herramientas usar (el RAG de la
Entrega 3, dos sensores y un actuador sobre SQL), recuerda la conversación por `thread_id` y está
expuesto como **API REST (FastAPI)** con logs JSON, métricas, trazas en LangSmith y guardrails.

**Asignatura:** Desarrollo de Sistemas de Inteligencia Artificial

**Integrantes:** Joaquín Soriano · Gustavo Caradonna · Melina Kanesky · Nicolas Bovino · Patricio Joandet

| Documento | Contenido |
|---|---|
| [`informe.md`](informe.md) | Informe: Entrega 1, Entrega 3 y TP Final (incluye la arquitectura por slices) |
| [`ficha_tecnica.md`](ficha_tecnica.md) | Ficha técnica del sistema |
| [`entregas/`](entregas/) | Entregas 1, 2 y 3 archivadas tal como se entregaron |

---

## Estructura: Vertical Slice Architecture

El código del sistema está organizado **por funcionalidad, no por capa técnica**. En vez de carpetas
`controllers/`, `services/` y `repositories/`, cada caso de uso es una carpeta (un *slice*) con todo lo
que necesita: su endpoint o su tool, sus modelos, su lógica y su acceso a datos. Para cambiar una
funcionalidad se toca una sola carpeta.

```
dsi_b/
├── app/                              ← el sistema en producción
│   ├── main.py                       ← arma la API registrando cada slice (único que los conoce a todos)
│   ├── features/                     ← slices HTTP: un caso de uso = una carpeta
│   │   ├── consultar/                   POST /consultar   modelos.py · handler.py · endpoint.py
│   │   ├── estado/                      GET  /estado/{thread_id}
│   │   ├── metricas/                    GET  /metricas
│   │   └── health/                      GET  /health
│   ├── herramientas/                 ← slices del agente: una capacidad = una carpeta
│   │   ├── conocimiento/                RETRIEVER: RAG de la E3   herramienta.py · retriever.py · indice.py · base_conocimiento.json
│   │   ├── disponibilidad/              SENSOR: stock (SQL)       herramienta.py · consultas.py
│   │   ├── precio/                      SENSOR: precio (SQL)      herramienta.py · consultas.py
│   │   └── reservas/                    ACTUADOR: reserva (SQL)   herramienta.py · consultas.py
│   ├── agente/                       ← el agente ReAct que compone los slices de herramientas
│   │                                    prompt.py · grafo.py · memoria.py · servicio.py
│   └── shared/                       ← solo lo transversal, sin lógica de negocio
│                                        config · llm · sql · guardrails · observabilidad · http
├── tests/
│   ├── security_tests.py             ← suite de seguridad (27 casos, sin API key)
│   └── test_arquitectura.py          ← verifica las reglas de los slices en cada corrida
├── evidencia/                        ← scripts y resultados: matriz, memoria vía HTTP, costos
├── entregas/                         ← Entregas 1, 2 y 3 (histórico)
└── data/                             ← lo genera el sistema al correr (en .gitignore)
```

**Reglas de dependencias**, verificadas por [`tests/test_arquitectura.py`](tests/test_arquitectura.py):

1. Ningún slice importa a otro slice.
2. `shared/` no conoce a nadie: ni slices, ni el agente, ni `main.py`.
3. Los slices de herramientas no dependen del agente ni de la API.
4. Solo `main.py` registra los slices HTTP.
5. El sistema no depende de las entregas archivadas.

Así, sumar una capacidad al agente es crear `app/herramientas/<nueva>/` y agregarla a la lista de
`app/herramientas/__init__.py`, y sumar un endpoint es crear `app/features/<nuevo>/` y registrar su
router en `main.py`. Nada más cambia.

## Cómo levantarlo en otra máquina

Probado con **Python 3.12** en Windows. Hace falta una API key gratuita de Google AI Studio
(https://aistudio.google.com/apikey). LangSmith es opcional: sin key, el sistema funciona igual y solo
se pierden las trazas.

**1. Clonar e instalar**

```bash
git clone https://github.com/gustavocaradonna/dsi_b.git
cd dsi_b
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Linux / macOS:          source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configurar**

```bash
cp .env.example .env          # en PowerShell: Copy-Item .env.example .env
```

Abrir `.env` y completar `GEMINI_API_KEY`. Opcional: `LANGSMITH_API_KEY` y
`LANGSMITH_PROJECT=alquiherramientas-tp-final`. El resto ya tiene valores por defecto.

**3. Levantar la API** (desde la raíz del repo)

```bash
uvicorn app.main:app --port 8000
```

En el **primer arranque** la API construye sola lo que no viene en el repo, dentro de `data/`: el
índice vectorial del slice de conocimiento (26 chunks), la base SQL con el catálogo y la memoria.
Tarda menos de un minuto y consume embeddings una sola vez. Está listo cuando el log muestra
`"evento": "api_iniciada"`.

Documentación interactiva: http://localhost:8000/docs

**4. Probar**

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/consultar -H "Content-Type: application/json" \
     -d '{"thread_id": "cliente-1", "mensaje": "¿Tienen hidrolavadora para el sábado?"}'
curl -X POST http://localhost:8000/consultar -H "Content-Type: application/json" \
     -d '{"thread_id": "cliente-1", "mensaje": "¿Y cuánto sale ese día?"}'
curl http://localhost:8000/estado/cliente-1
curl http://localhost:8000/metricas
```

En PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/consultar -Method Post -ContentType "application/json; charset=utf-8" `
  -Body '{"thread_id": "cliente-1", "mensaje": "¿Tienen hidrolavadora para el sábado?"}'
Invoke-RestMethod http://localhost:8000/estado/cliente-1
```

Para ver la memoria después de un reinicio: cortar uvicorn (Ctrl+C), volver a levantarlo y pedir
`/estado/cliente-1`, o seguir la conversación con el mismo `thread_id`.

**5. Tests** (no llaman al LLM ni necesitan API key)

```bash
python -m pytest -v
```

Corre la suite de seguridad y las reglas de arquitectura. Usan una carpeta de datos temporal: nunca
tocan `data/`.

**6. Evidencia reproducible** (usan el modelo real)

```bash
python evidencia/matriz_validacion.py     # Parte A: 4 escenarios con chequeos automáticos
python evidencia/demo_api_http.py         # Parte B: memoria vía HTTP antes y después de reiniciar
python evidencia/analisis_costos.py       # Parte C: tokens, costo y latencia desde LangSmith
```

## Cómo fluye una consulta

```
POST /consultar ─► features/consultar ─► shared/guardrails (entrada) ──(bloquea: 400, 0 tokens)
                                            │ longitud · prompt injection
                                            ▼
                                        agente ReAct (agente/grafo.py) ◄── memoria SQLite por thread_id
                                            │  agente ⇄ herramientas, como máximo MAX_ITERACIONES rondas
                                            ├─ herramientas/conocimiento    chunks k=8 → juez LLM → documento padre
                                            ├─ herramientas/disponibilidad  stock real (SQL)
                                            ├─ herramientas/precio          precio y depósito (SQL)
                                            └─ herramientas/reservas        reserva 'pendiente' (SQL, solo con stock)
                                            ▼
                                        shared/guardrails (salida): enmascarado de DNI, teléfono, email, tarjeta
                                            ▼
                                        respuesta + log JSON + /metricas + traza en LangSmith
```

## Configuración

| Variable | Default | Para qué |
|---|---|---|
| `GEMINI_API_KEY` | — (**obligatoria**) | LLM y embeddings |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Modelo del agente y del juez de relevancia |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Embeddings del índice vectorial |
| `MAX_ITERACIONES` | `5` | Rondas agente → herramientas por mensaje |
| `DIR_DATOS` | `data` | Carpeta de los datos generados (relativa a la raíz) |
| `RUTA_MEMORIA` | `memoria_agente.sqlite` | Archivo de la memoria, dentro de `DIR_DATOS` |
| `PRECIO_ENTRADA_USD_1M` / `PRECIO_SALIDA_USD_1M` | `0.30` / `2.50` | Costo estimado en `/metricas` |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | `true` / — / — | Trazas (opcional) |
| `RAGAS_LLM_MODEL` | el de `GEMINI_MODEL` | Juez de RAGAS (solo para la E3 archivada) |

> **`.env` está en `.gitignore` desde el primer commit y nunca se sube.** Si alguna vez se filtra
> una key, no alcanza con borrarla: hay que **rotarla**. `data/` (memoria, bases, logs) tampoco se
> sube: la memoria guarda los mensajes de los clientes tal cual.

## Entregas anteriores

Las Entregas 1, 2 y 3 están en [`entregas/`](entregas/), cada una en su carpeta y tal como se
entregó. Ahí está el índice de archivos y cómo correr cada una.
