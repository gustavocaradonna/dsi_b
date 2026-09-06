# AlquiHerramientas — TP Integrador Entrega 1

Pipeline de extracción validada para el asistente de WhatsApp de **AlquiHerramientas**, un local
ficticio de alquiler de herramientas. Convierte mensajes de texto libre en datos estructurados
que cumplen un contrato, para que el backend pueda consultar catálogo y gestionar reservas.

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
| [`app.py`](app.py) | Pipeline con Gemini + Structured Outputs y lote de prueba (C.2, C.3) |
| [`resultados_lote.md`](resultados_lote.md) | Tabla de resultados de los 6 casos (C.3) |
| [`anatomia_token.py`](anatomia_token.py) | Análisis de tokens ES vs EN y costo del prompt (A.4) |
| [`evidencia_alucinacion.py`](evidencia_alucinacion.py) | Réplica de "El Proveedor Enojado" (A.2) |
| [`sql/schema.sql`](sql/schema.sql) | Esquema de base de datos (B.5.b) |
| [`.env.example`](.env.example) | Variables de entorno, sin valores reales |

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

> **`.env` está en `.gitignore` desde el primer commit y nunca se sube.** Si alguna vez se
> filtra una key, no alcanza con borrarla: hay que **rotarla** en AI Studio.

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
   └─ Salida: SolicitudAlquiler validada, lista para el backend
```

El JSON Schema que se le pasa a Gemini es **deliberadamente más permisivo** que el modelo
Pydantic: el LLM garantiza la *forma*, Pydantic garantiza las *reglas de negocio*. Si fueran
idénticos nunca se podría observar un `ValidationError` — y esa aduana es el punto del TP.

Las cuatro intenciones (`consultar_disponibilidad`, `consultar_precio`, `solicitar_reserva`,
`fuera_de_alcance`) son las mismas en la Matriz de Intenciones del informe, en el `Literal` de
`schemas.py`, en el System Prompt y en la tabla de resultados.
