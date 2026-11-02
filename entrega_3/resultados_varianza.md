# Varianza de los jueces LLM (corrección de B.4)

**Fecha del reporte:** 2026-11-02

## 1. Juez de relevancia del reranker

Modelo `gemini-3.5-flash-lite`, 5 repeticiones sobre los mismos 8 candidatos (recuperados una sola vez). Corte de selección: puntaje ≥ 6.

### B.1 — multi-parte: descartar la ficha ruidosa y quedarse con 4 políticas

> Quiero alquilar la hormigonera: ¿me la llevan a casa, qué papeles necesito, cuándo puedo cancelar sin cargo y qué pasa si se rompe?

**Conjunto seleccionado idéntico en 5/5 repeticiones** (el más frecuente: DOC-011#c0, DOC-012#c0, DOC-013#c0, DOC-015#c0).

| Chunk | Distancia | Puntajes | Media | Desvío | Rango | Veces ≥ corte |
|---|---|---|---|---|---|---|
| DOC-009#c0 | 0.266 | 3, 4, 5, 5, 5 | 4.4 | 0.80 | 2 | 0/5 |
| DOC-012#c0 | 0.2945 | 10, 10, 9, 10, 10 | 9.8 | 0.40 | 1 | 5/5 |
| DOC-011#c0 | 0.2982 | 10, 10, 9, 10, 10 | 9.8 | 0.40 | 1 | 5/5 |
| DOC-013#c0 | 0.3182 | 10, 10, 10, 10, 10 | 10.0 | 0.00 | 0 | 5/5 |
| DOC-015#c0 | 0.3208 | 10, 10, 10, 10, 10 | 10.0 | 0.00 | 0 | 5/5 |
| DOC-011#c1 | 0.3312 | 4, 3, 4, 6, 6 | 4.6 | 1.20 | 3 | 2/5 |
| DOC-010#c0 | 0.3364 | 2, 3, 3, 4, 3 | 3.0 | 0.63 | 2 | 0/5 |
| DOC-005#c1 | 0.3435 | 0, 0, 0, 2, 2 | 0.8 | 0.98 | 2 | 0/5 |

### C6 — multi-parte con ficha necesaria

> Alquilo la hidrolavadora para el finde: ¿qué necesito tener en casa para usarla, qué hago si deja de andar, y cómo hago para devolverla si el domingo está cerrado?

**Conjunto seleccionado idéntico en 5/5 repeticiones** (el más frecuente: DOC-003#c1, DOC-014#c0, DOC-015#c0).

| Chunk | Distancia | Puntajes | Media | Desvío | Rango | Veces ≥ corte |
|---|---|---|---|---|---|---|
| DOC-014#c0 | 0.2842 | 10, 10, 10, 10, 10 | 10.0 | 0.00 | 0 | 5/5 |
| DOC-011#c0 | 0.2919 | 0, 2, 2, 1, 2 | 1.4 | 0.80 | 2 | 0/5 |
| DOC-015#c0 | 0.3013 | 10, 10, 9, 10, 10 | 9.8 | 0.40 | 1 | 5/5 |
| DOC-003#c0 | 0.3059 | 3, 4, 5, 4, 5 | 4.2 | 0.75 | 2 | 0/5 |
| DOC-003#c1 | 0.3125 | 10, 10, 10, 10, 10 | 10.0 | 0.00 | 0 | 5/5 |
| DOC-011#c1 | 0.317 | 0, 1, 1, 0, 1 | 0.6 | 0.49 | 1 | 0/5 |
| DOC-012#c0 | 0.3265 | 3, 3, 3, 3, 3 | 3.0 | 0.00 | 0 | 0/5 |
| DOC-010#c0 | 0.3267 | 0, 2, 2, 2, 2 | 1.6 | 0.80 | 2 | 0/5 |

### E2 — escape: ningún chunk debería pasar el corte

> ¿Alquilan motosierras para podar árboles?

**Conjunto seleccionado idéntico en 5/5 repeticiones** (el más frecuente: vacío → frase de escape).

| Chunk | Distancia | Puntajes | Media | Desvío | Rango | Veces ≥ corte |
|---|---|---|---|---|---|---|
| DOC-007#c0 | 0.3202 | 2, 2, 2, 2, 1 | 1.8 | 0.40 | 1 | 0/5 |
| DOC-011#c0 | 0.3256 | 1, 1, 1, 1, 1 | 1.0 | 0.00 | 0 | 0/5 |
| DOC-005#c1 | 0.326 | 1, 1, 0, 1, 0 | 0.6 | 0.49 | 1 | 0/5 |
| DOC-012#c0 | 0.3547 | 1, 1, 1, 1, 1 | 1.0 | 0.00 | 0 | 0/5 |
| DOC-015#c0 | 0.3581 | 1, 1, 1, 1, 1 | 1.0 | 0.00 | 0 | 0/5 |
| DOC-010#c0 | 0.363 | 1, 1, 1, 1, 1 | 1.0 | 0.00 | 0 | 0/5 |
| DOC-005#c0 | 0.3638 | 1, 2, 1, 1, 1 | 1.2 | 0.40 | 1 | 0/5 |
| DOC-010#c1 | 0.3681 | 1, 1, 1, 1, 1 | 1.0 | 0.00 | 0 | 0/5 |

## 2. Juez de RAGAS

Juez `gemini-3.1-flash-lite` (el mismo de la tabla C.3), **las mismas 13 respuestas del avanzado** evaluadas 3 veces. La repetición 1 es la corrida entregada (`metricas_avanzado.json`).

| Métrica | Rep. 1 | Rep. 2 | Rep. 3 | Media | Desvío entre corridas | Desvío medio por pregunta | Rango máx. por pregunta |
|---|---|---|---|---|---|---|---|
| Faithfulness | 0.690 | 0.690 | 0.690 | 0.690 | 0.000 | 0.000 | 0.000 |
| Answer Relevancy | 0.665 | 0.664 | 0.665 | 0.665 | 0.000 | 0.001 | 0.018 |
| Context Precision | 0.462 | 0.462 | 0.462 | 0.462 | 0.000 | 0.000 | 0.000 |
| Context Recall | 0.795 | 0.795 | 0.795 | 0.795 | 0.000 | 0.000 | 0.000 |

Preguntas cuyo puntaje cambia entre repeticiones (rango > 0.2):

- Ninguna: con el mismo juez, cada pregunta recibe el mismo puntaje en todas las repeticiones.

## 3. Variación entre jueces distintos (la que sí pesa)

Las mismas respuestas de las 10 preguntas originales, evaluadas por `gemini-3.5-flash-lite` (corrida 1) y por `gemini-3.1-flash-lite` (corrida de referencia de C.3).

| Pipeline | Métrica | Juez 3.5-flash-lite | Juez 3.1-flash-lite | Diferencia | Preguntas con diferencia > 0.2 |
|---|---|---|---|---|---|
| basico | Faithfulness | 0.810 | 0.638 | -0.172 | 3/10 (S3, E1, I2) |
| basico | Answer Relevancy | 0.767 | 0.698 | -0.069 | 1/10 (E1) |
| basico | Context Precision | 0.733 | 0.783 | +0.050 | 3/10 (C3, E1, E2) |
| basico | Context Recall | 0.900 | 0.900 | +0.000 | 0/10 (—) |
| avanzado | Faithfulness | 0.760 | 0.617 | -0.143 | 2/10 (S3, I2) |
| avanzado | Answer Relevancy | 0.692 | 0.696 | +0.004 | 0/10 (—) |
| avanzado | Context Precision | 0.700 | 0.600 | -0.100 | 1/10 (C1) |
| avanzado | Context Recall | 0.800 | 0.800 | +0.000 | 0/10 (—) |
