# Resultados de las Killer Queries (B.6)

**Umbral de aceptacion (distancia coseno):** 0.32 — ver C.2 en informe_entrega2.md.  
**Fecha de corrida:** 2026-09-12

| # | Consulta | Que pone a prueba | Resultado esperado | Resultado real | Paso |
|---|---|---|---|---|---|
| 1 | tengo que picar los cascotes de un piso viejo antes de embaldosar de nuevo | Poder semantico: jerga regional sin palabras exactas del documento | DOC-008 (martillo_demoledor) arriba, aunque 'cascotes' y 'embaldosar' no estan en su texto | 1ro: `DOC-008` (dist 0.2896) | Si |
| 2 | necesito un taladro percutor para el sabado | El metadato salva el dia: sin filtro el taladro de baja queda pegado al activo (distancias casi identicas), el filtro lo saca del todo | Sin filtro, DOC-002 (descontinuado) queda en el top-2 a una distancia casi identica a DOC-001; con el where, DOC-002 desaparece de los resultados | con filtro: `['DOC-001', 'DOC-005', 'DOC-011']` (activos=[True, True, True]); sin filtro DOC-002 aparecia en el top-2 (dist 0.2971 vs. 0.2910 de DOC-001) | Si |
| 3 | necesito alquilar un generador electrico portatil | Prueba de estres: consulta fuera de catalogo | Ninguna distancia deberia superar el umbral de aceptacion -> 'no tengo eso' | mejor distancia 0.3507 (DOC-005) | Si |
