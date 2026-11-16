# Análisis de costos y latencia desde LangSmith (TP Final, Parte C)

**Proyecto LangSmith:** `alquiherramientas-entrega3` · **Trazas analizadas:** 9 corridas de `agente_alquiherramientas` desde 2026-11-16 (matriz de validación, demo HTTP y pruebas) · **Fecha del reporte:** 2026-11-16

El costo de cada traza es el `total_cost` que calcula LangSmith con su tabla de precios del modelo. Coincide con la tarifa configurada en `app/shared/config.py` (USD 0.30 / 2.50 por millón de tokens de entrada / salida), así que `/metricas` y LangSmith dan el mismo número.

## Resumen por consulta

| Métrica | Valor |
|---|---|
| Tokens por consulta (promedio / p95) | 4,566 / 6,530 |
| Costo por consulta (promedio / p95) | USD 0.00186 / USD 0.00375 |
| Latencia (promedio / p50 / p95) | 15.8 s / 10.0 s / 35.4 s |
| Llamadas al LLM por consulta (agente + juez) | 1.9 + 0.3 |

## Dónde se van los tokens

| Componente | Tokens | Participación |
|---|---|---|
| Agente (decidir herramientas + redactar) | 37,842 | 92% |
| Juez de relevancia (dentro de `buscar_informacion`) | 3,254 | 8% |

| Tipo de consulta | Consultas | Tokens promedio | Costo promedio | Latencia promedio |
|---|---|---|---|---|
| Usa el RAG (`buscar_informacion`) | 2 | 6,041 | USD 0.00327 | 20.0 s |
| Solo SQL o sin herramientas | 7 | 4,145 | USD 0.00146 | 14.6 s |

## Proyección a 3,000 consultas por día

| Período | Costo estimado |
|---|---|
| Día | USD 5.59 |
| Mes (30 días) | USD 167.60 |
| Año | USD 2,039.08 |

## Detalle por traza

| Inicio (UTC) | Herramientas | Llamadas LLM (agente/juez) | Tokens entrada/salida | Costo USD | Latencia |
|---|---|---|---|---|---|
| 22:07:05 | consultar_precio, consultar_disponibilidad | 2/0 | 4,331/154 | 0.00168 | 6.8 s |
| 22:07:32 | buscar_informacion, buscar_informacion | 2/2 | 5,715/815 | 0.00375 | 30.1 s |
| 22:11:14 | buscar_informacion | 2/1 | 5,043/509 | 0.00279 | 10.0 s |
| 22:11:24 | consultar_disponibilidad | 2/0 | 4,254/96 | 0.00152 | 8.9 s |
| 22:11:33 | consultar_disponibilidad | 2/0 | 4,242/107 | 0.00154 | 15.1 s |
| 22:11:48 | crear_reserva | 2/0 | 4,727/148 | 0.00179 | 24.9 s |
| 22:12:13 | — | 1/0 | 2,020/29 | 0.00068 | 4.9 s |
| 22:13:14 | consultar_disponibilidad | 2/0 | 4,203/86 | 0.00148 | 35.4 s |
| 22:14:18 | consultar_precio | 2/0 | 4,547/70 | 0.00154 | 6.5 s |
