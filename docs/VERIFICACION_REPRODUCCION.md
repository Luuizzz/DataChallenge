# Verificación de la reproducción

Ejecutamos `python pipeline/run_all.py` completo con el código de este repositorio sobre la extracción real (los 8 Parquet de `extract/10_dump.sql`) y comparamos las cifras con las del documento final. Las del documento salen de la ejecución exploratoria original, que tenía el mismo código pero sin el modo determinista.

## Determinismo

Ejecutamos dos veces seguidas el modelo de ingreso (05b), la alerta (07) y la simulación (09) sobre la misma base. Los archivos de salida son **idénticos byte a byte**. Lo garantizan estas medidas:

- Semillas fijas en el bootstrap (`default_rng(42)`), en la simulación y en LightGBM (`random_state`, `deterministic=True`, `force_row_wise=True`).
- Consultas con orden total (`ORDER BY ALL` o claves completas) antes de muestrear o entrenar.
- Desempates explícitos en `LIMIT` (`ORDER BY n DESC, cid`) y en `arg_min`.
- El censo de la alerta acumula un solo valor por instante, así que no hay empates en la suma acumulada.

## Cifras del documento frente a la reproducción

| Resultado | Documento | Reproducción |
|---|---|---|
| Camas efectivas calibradas (C) / k | 269 / 0,55 | 269 / 0,55 |
| Combinado 50 % / −50 %: Δ mediana (h) | −7,3 | −7,3 |
| Combinado: Δ p90 (h) | −13,8 | −13,6 |
| +10 camas: Δ mediana (h) | −9,4 | −9,4 |
| Altas a.m. 50 % / interconsultas −50 %: Δ mediana (h) | −5,3 / −1,9 | −5,3 / −1,9 |
| Alerta a 3 h: precisión (IC 95 %) | 0,798 (0,712–0,867) | 0,797 (0,714–0,865) |
| Alerta a 3 h: recall / MAE | 0,643 / 16,32 | 0,658 / 16,31 |
| Modelo de ingreso a 3 h sin fuga: AUC (IC 95 %) | 0,712 (0,704–0,720) | 0,713 (0,706–0,721) |
| AUC por ventana 1 h / 3 h / 6 h · logística | 0,697 / 0,713 / 0,722 · 0,668 | 0,696 / 0,713 / 0,720 · 0,668 |
| Decisión top 20 %: ingresos anticipados/día · antelación (h) | 18,4 · 19,6 | 18,4 · 20,0 |
| Interconsultas ajustadas: ortopedia / urología (h) | +22,0 / +17,6 | +22,0 / +17,6 |
| Validación 2026: mediana simulada (h) | 13,9 | 13,9 |
| Recalibración 2026: Δ combinado (h) | −12,9 | −13,1 |

Las diferencias quedan dentro de los intervalos de confianza publicados y no cambian ninguna conclusión ni el orden de las medidas. Episodios, etapas y censo tienen exactamente las mismas filas que en la ejecución original (2.336.981 / 3.281.496 / 31.392).
