# Guía rápida: dashboard de Power BI en ~45 minutos

**Requisito:** Power BI Desktop, que no está instalado en este equipo. Se puede instalar desde Microsoft Store ("Power BI Desktop") o con `winget install Microsoft.PowerBI`. Para publicar hace falta una cuenta institucional (el servicio de Power BI no admite cuentas personales).

## 1. Cargar los datos (5 min)

*Inicio → Obtener datos → Carpeta* → la carpeta de los CSV (en el proyecto final se usa el parámetro `RutaDatos`, por defecto `C:\datachallenge\powerbi\`) → **Transformar datos**. Otra opción, más simple: *Obtener datos → Texto/CSV* para cada archivo.

Cargar estos CSV: `dim_fecha`, `f_hora`, `f_kpi_mensual`, `f_espera_hora_dia`, `f_altas_ingresos_hora`, `f_interconsultas`, `f_n_servicios`, `f_flujo_transiciones`, `f_pronostico_3h`, `f_simulacion_escenarios`, `f_simulacion_sensibilidad`, `f_modelo_ingreso_deciles`, `f_modelos_metricas`, `f_calidad_datos`, `f_edad`.

**Importante:** en Power Query, revisar que los decimales usen punto. Si se convierten mal, usar *Cambiar tipo → Usando configuración regional → Inglés (Estados Unidos)*.

## 2. Relaciones (2 min)

En la vista de modelo, relacionar `dim_fecha[fecha]` con `f_hora[fecha]` (1 a varios). El resto de tablas va suelta.

## 3. Medidas DAX (copiar y pegar)

Crearlas en `f_hora` o en una tabla vacía llamada `_Medidas`:

```DAX
Censo urgencias medio = AVERAGE ( f_hora[censo_urgencias] )
Censo hospitalización medio = AVERAGE ( f_hora[censo_hospitalizacion] )
Horas saturadas = CALCULATE ( COUNTROWS ( f_hora ), f_hora[saturado_urgencias] = TRUE () )
% horas saturadas = DIVIDE ( [Horas saturadas], COUNTROWS ( f_hora ) )
Llegadas (>=15 min) = SUM ( f_hora[llegadas_15min] )
Ingresos a hospitalización = SUM ( f_hora[ingresos_hosp] )
Altas = SUM ( f_hora[altas_hosp] )
% altas antes 12h = DIVIDE ( CALCULATE ( [Altas], f_hora[hora] < 12 ), [Altas] )

Mediana h hasta hosp (mes) = AVERAGE ( f_kpi_mensual[mediana_h_hasta_hosp] )
P90 h hasta hosp (mes) = AVERAGE ( f_kpi_mensual[p90_h_hasta_hosp] )
% ingresados > 24h = AVERAGE ( f_kpi_mensual[pct_ingresados_mas24h] ) / 100

Alertas correctas = CALCULATE ( COUNTROWS ( f_pronostico_3h ), f_pronostico_3h[alerta] = TRUE (), f_pronostico_3h[saturado_real] = TRUE () )
Precisión alerta 3h = DIVIDE ( [Alertas correctas], CALCULATE ( COUNTROWS ( f_pronostico_3h ), f_pronostico_3h[alerta] = TRUE () ) )
Recall alerta 3h = DIVIDE ( [Alertas correctas], CALCULATE ( COUNTROWS ( f_pronostico_3h ), f_pronostico_3h[saturado_real] = TRUE () ) )
```

## 4. Páginas y visuales

> El informe entregado (`pbip/`) ya está construido y se regenera con `13_generar_visuales_v2.py`; su orden de páginas final está en `README.md`. Esta sección sirve para montarlo a mano.

**P1 · Resumen**
- Tarjetas: `Mediana h hasta hosp (mes)`, `% ingresados > 24h`, `Censo hospitalización medio`, `% altas antes 12h`, `% horas saturadas`.
- Gráfico de líneas: `f_kpi_mensual[anio_mes]` frente a `mediana_h_hasta_hosp` y `p90_h_hasta_hosp`.
- Segmentador: `dim_fecha[anio]`.
- Cuadro de texto con 3 hallazgos (copiar del resumen ejecutivo del documento).

**P2 · Flujo**
- Sankey (visual de AppSource "Sankey Chart"): Origen = `f_flujo_transiciones[origen]`, Destino = `destino`, Peso = `n`. Filtrar sin "Rehabilitación ambulatoria" para centrarse en urgencias.
- Barras: `f_edad[grupo_edad]` frente a `tasa_ingreso_pct` y `mediana_h_hasta_hosp`.

**P3 · Cuellos de botella**
- Matriz con formato condicional (mapa de calor): filas `f_espera_hora_dia[hora_llegada]`, columnas `dia_semana_num`, valores `mediana_h_hasta_hosp` (escala de color blanco → rojo).
- Columnas agrupadas: `f_altas_ingresos_hora[hora]` frente a `altas_hosp` e `ingresos_hosp`.
- Barras: `f_interconsultas[servicio]` frente a `mediana_h_con` y `mediana_h_sin`.
- Líneas: `f_n_servicios[n_servicios]` frente a `mediana_h_hasta_hosp`.

**P4 · Congestión y alerta**
- Líneas: `f_hora[fecha_hora]` frente a `censo_urgencias` y `censo_hospitalizacion`, con línea constante en 287 (panel *Análisis*).
- Líneas: `f_pronostico_3h[fecha_hora_objetivo]` frente a `censo_real` y `censo_pronosticado_3h`.
- Tarjetas: `Precisión alerta 3h`, `Recall alerta 3h`.

**P5 · Mejoras (simulación)**
- Barras horizontales: `f_simulacion_escenarios[escenario]` frente a `delta_mediana_h` y `delta_p90_h`.
- Tabla: `escenario`, `mediana_h`, `pct_mas24h`, `horas_paciente_ahorradas_anio`.
- Líneas: `f_simulacion_sensibilidad[C]` frente a `delta_altas_am_30pct` y `delta_interconsulta_quir_-50pct` (filtrar k = 0,55). Muestra que el sistema opera al límite.

**P6 · Datos y supuestos**
- Tabla `f_calidad_datos`.
- Tabla `f_modelos_metricas`.
- Columnas: `f_modelo_ingreso_deciles`.
- Cuadro de texto con los supuestos S1–S5 del documento.

**P7 · Rigor y robustez**
- Tarjetas: `Ingresos anticipados por día`, `Horas de antelación (mediana)`, `AUC modelo ingreso 3h`.
- Barras: `f_interconsultas_ajustado[servicio]` frente a `crudo_h` y `ajustado_h`.
- Columnas: `f_modelo_ventanas[modelo]` frente a `auc` (ordenar por `orden`).
- Tabla: `f_validacion_2026`.

## 5. Publicar

*Archivo → Publicar → Mi área de trabajo* (cuenta institucional) → en el servicio, *Compartir* con los evaluadores. **No usar "Publicar en la web"**: deja el informe público.
