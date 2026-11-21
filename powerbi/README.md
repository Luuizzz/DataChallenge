# Datos para Power BI (todos agregados, sin datos por paciente)

Se generan con `11_powerbi.py`. El periodo va del 15 de enero de 2023 al 30 de abril de 2026 (mayo a julio de 2026 se excluye por estar incompleto). Los grupos con menos de 10 casos se suprimen.

## Modelo

- `dim_fecha[fecha]` → `f_hora[fecha]` (1:*)
- `f_kpi_mensual[anio_mes]` ↔ `dim_fecha[anio_mes]` (*:1, se puede usar con filtro de año)
- El resto son tablas independientes para visuales concretos.

| Tabla | Grano | Para qué |
|---|---|---|
| `f_hora` | 1 fila por hora | censos de urgencias y hospitalización, llegadas, ingresos, altas, horas saturadas |
| `f_kpi_mensual` | mes | KPIs: tasa de ingreso, mediana y p90 hasta hospitalización, % > 24 h, % ≤ 4 h, % > 12 h, estancia |
| `f_espera_hora_dia` | hora de llegada × día | mapa de calor de la espera hasta hospitalización |
| `f_altas_ingresos_hora` | hora del día | desajuste entre altas e ingresos |
| `f_edad` | grupo de edad | tasa de ingreso y espera |
| `f_interconsultas` | servicio | mediana con y sin cada interconsulta |
| `f_n_servicios` | número de servicios | dosis-respuesta |
| `f_flujo_transiciones` | origen → destino | diagrama de Sankey del flujo |
| `f_pronostico_3h` | hora (ene–abr 2026) | censo real frente a pronóstico a 3 h, alertas |
| `f_modelos_metricas`, `f_modelo_ingreso_deciles` | métrica / decil | desempeño de los modelos |
| `f_simulacion_escenarios`, `f_simulacion_sensibilidad` | escenario / parámetro | impacto de las mejoras |
| `f_calidad_datos` | problema | transparencia metodológica |
| `f_interconsultas_ajustado` | servicio | efecto crudo frente a ajustado (regresión cuantil) con IC 95 % |
| `f_modelo_ventanas`, `f_decision` | modelo / métrica | AUC por ventana (1, 3 y 6 h) y logística; análisis de decisión del 20 % de mayor riesgo |
| `f_validacion_2026` | indicador | validación fuera de muestra de la simulación (observado 2026, C = 269 y C = 260) |

## Páginas del informe

1. **Resumen**: tarjetas (mediana hasta hospitalización, % > 24 h, censo medio, horas saturadas) y tendencia mensual.
2. **Cuellos de botella**: mapa de calor hora × día, altas frente a ingresos por hora, interconsultas.
3. **Congestión y alerta**: censo horario con umbral y pronóstico a 3 h, con precisión y recall.
4. **Mejoras (simulación)**: selector de escenario con sus tarjetas (Δ mediana, Δ p90, horas-paciente/año), escenarios y sensibilidad respecto al número de camas.
5. **Flujo, modelos y datos**: transiciones entre etapas, edad, deciles del modelo de ingreso, calidad de datos.
6. **Rigor y robustez**: interconsultas ajustadas, AUC por ventana, análisis de decisión y validación fuera de muestra 2026.
7. **Seguimiento del piloto**: % de altas antes de las 12 h frente a la meta (30 %), horas saturadas y distribución horaria de altas e ingresos, con selector de año.

Para compartir: **no usar "Publicar en la web"**; compartir con cuentas de la organización.
