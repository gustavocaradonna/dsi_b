# Recalibracion del umbral de aceptacion

**Fecha de corrida:** 2026-10-19  
**Consultas:** 24 positivas y 16 negativas, ninguna repetida de las Killer Queries de la Entrega 2.  
**Metodo:** el umbral se elige SOLO con el set de calibracion (maximo balanced accuracy, punto medio entre empatados) y se mide sobre el set de validacion, que no participo.

## Resultado

| | Umbral | TP | FN | TN | FP | Recall positivas | Recall negativas | Balanced acc. |
|---|---|---|---|---|---|---|---|---|
| Calibracion | 0.36 | 12 | 0 | 5 | 3 | 1.00 | 0.62 | 0.812 |
| **Validacion (held-out)** | 0.36 | 12 | 0 | 8 | 0 | 1.00 | 1.00 | **1.000** |
| Validacion con el umbral viejo | 0.32 | 10 | 2 | 8 | 0 | 0.83 | 1.00 | 0.917 |

Peor positiva de calibracion: 0.3467 — mejor negativa de calibracion: 0.3142 (hay solapamiento).  
Top-1 correcto en las positivas: 23/24.

## Killer Queries de la Entrega 2 (ya no se usan para elegir el umbral)

| Consulta | Top-1 | Distancia | Con el umbral nuevo |
|---|---|---|---|
| tengo que picar los cascotes de un piso viejo antes de embaldosar de nuevo | DOC-008 | 0.2896 | acepta |
| necesito un taladro percutor para el sabado | DOC-001 | 0.2910 | acepta |
| necesito alquilar un generador electrico portatil | DOC-005 | 0.3507 | acepta |

## Detalle por consulta

### Calibracion

| Tipo | Consulta | Top-1 | Esperado | Distancia | Decision con umbral |
|---|---|---|---|---|---|
| positiva | si cancelo la reserva me devuelven la plata | DOC-013 | DOC-013 | 0.2555 | acepta |
| positiva | me lo pueden traer a mi casa | DOC-012 | DOC-012 | 0.2667 | acepta |
| positiva | tienen algo para lavar la vereda y el auto | DOC-003 | DOC-003 | 0.2802 | acepta |
| positiva | necesito romper un contrapiso | DOC-008 | DOC-008 | 0.2806 | acepta |
| positiva | que papeles tengo que llevar para retirar | DOC-011 | DOC-011 | 0.2806 | acepta |
| positiva | cuanta plata tengo que dejar de garantia | DOC-010 | DOC-010 | 0.2991 | acepta |
| positiva | necesito dejar lisa una mesa de madera antes de barnizarla | DOC-004 | DOC-004 | 0.3133 | acepta |
| positiva | quiero cortar placas de mdf derechitas | DOC-006 | DOC-006 | 0.3136 | acepta |
| positiva | tengo que cortar unos caños de hierro | DOC-005 | DOC-005 | 0.3239 | acepta |
| positiva | quiero hacer unos agujeros en la pared para colgar una repisa | DOC-001 | DOC-001 | 0.3369 | acepta |
| positiva | voy a hacer la mezcla para unas columnas | DOC-009 | DOC-009 | 0.3412 | acepta |
| positiva | tengo que pintar la fachada de una casa de dos pisos | DOC-007 | DOC-007 | 0.3467 | acepta |
| negativa | necesito una escalera de 7 metros | DOC-007 | — | 0.3142 | **acepta (FP)** |
| negativa | alquilan cortadoras de cesped | DOC-005 | — | 0.3393 | **acepta (FP)** |
| negativa | necesito una motosierra para cortar un arbol | DOC-005 | — | 0.3449 | **acepta (FP)** |
| negativa | tienen soldadora electrica | DOC-009 | — | 0.3811 | rechaza |
| negativa | venden pintura latex para exterior | DOC-007 | — | 0.4161 | rechaza |
| negativa | me recomendas una receta de empanadas | DOC-016 | — | 0.4603 | rechaza |
| negativa | como esta el clima mañana en cordoba | DOC-014 | — | 0.4638 | rechaza |
| negativa | cual es la capital de francia | DOC-014 | — | 0.5162 | rechaza |

### Validacion (held-out)

| Tipo | Consulta | Top-1 | Esperado | Distancia | Decision con umbral |
|---|---|---|---|---|---|
| positiva | hasta que hora puedo devolver la herramienta un viernes | DOC-014 | DOC-014 | 0.1749 | acepta |
| positiva | como uso las herramientas electricas sin lastimarme | DOC-016 | DOC-016 | 0.1878 | acepta |
| positiva | si devuelvo la amoladora con un golpe me cobran | DOC-015 (doc incorrecto) | DOC-010 | 0.2243 | acepta |
| positiva | se me rompio la maquina mientras la usaba, que hago | DOC-015 | DOC-015 | 0.2325 | acepta |
| positiva | necesito algo para trabajar en altura arreglando el techo | DOC-007 | DOC-007 | 0.2646 | acepta |
| positiva | necesito una betonera para un fin de semana | DOC-009 | DOC-009 | 0.2655 | acepta |
| positiva | que pasa si no voy a buscar la reserva y no aviso | DOC-013 | DOC-013 | 0.2769 | acepta |
| positiva | abren el sabado a la tarde | DOC-014 | DOC-014 | 0.2956 | acepta |
| positiva | necesito una mechadora para poner tarugos en el ladrillo | DOC-001 | DOC-001 | 0.3070 | acepta |
| positiva | quiero sacarle el verdin al patio con agua a presion | DOC-003 | DOC-003 | 0.3155 | acepta |
| positiva | tengo que cortar porcelanato | DOC-005 | DOC-005 | 0.3217 | acepta |
| positiva | quiero sacar el revoque viejo que esta todo flojo | DOC-008 | DOC-008 | 0.3397 | acepta |
| negativa | necesito un elevador de autos para el taller | DOC-007 | — | 0.3659 | rechaza |
| negativa | alquilan un compresor de aire para pintar con soplete | DOC-007 | — | 0.3673 | rechaza |
| negativa | alquilan carpas para un evento | DOC-007 | — | 0.3700 | rechaza |
| negativa | tienen bordeadora para el pasto | DOC-014 | — | 0.3823 | rechaza |
| negativa | tienen grupo electrogeno | DOC-009 | — | 0.4223 | rechaza |
| negativa | me ayudas con la tarea de matematica | DOC-014 | — | 0.4371 | rechaza |
| negativa | como hago para sacar el pasaporte | DOC-011 | — | 0.4459 | rechaza |
| negativa | quien gano el partido de river ayer | DOC-014 | — | 0.4903 | rechaza |

## Curva sobre calibracion

| Umbral | Recall positivas | Recall negativas | Balanced |
|---|---|---|---|
| 0.250 | 0.00 | 1.00 | 0.500 |
| 0.260 | 0.08 | 1.00 | 0.542 |
| 0.270 | 0.17 | 1.00 | 0.583 |
| 0.280 | 0.17 | 1.00 | 0.583 |
| 0.290 | 0.42 | 1.00 | 0.708 |
| 0.300 | 0.50 | 1.00 | 0.750 |
| 0.310 | 0.50 | 1.00 | 0.750 |
| 0.320 | 0.67 | 0.88 | 0.771 |
| 0.330 | 0.75 | 0.88 | 0.812 |
| 0.340 | 0.83 | 0.75 | 0.792 |
| 0.350 | 1.00 | 0.62 | 0.812 |
| 0.360 | 1.00 | 0.62 | 0.812 |
| 0.370 | 1.00 | 0.62 | 0.812 |
| 0.380 | 1.00 | 0.62 | 0.812 |
| 0.390 | 1.00 | 0.50 | 0.750 |
| 0.400 | 1.00 | 0.50 | 0.750 |
| 0.410 | 1.00 | 0.50 | 0.750 |
| 0.420 | 1.00 | 0.38 | 0.688 |
| 0.430 | 1.00 | 0.38 | 0.688 |
| 0.440 | 1.00 | 0.38 | 0.688 |
| 0.450 | 1.00 | 0.38 | 0.688 |
