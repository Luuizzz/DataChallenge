"""v2: informe con tema propio, cabeceras, tarjetas modernas (cardVisual), colores por serie, etiquetas,
linea de umbral y mapa de calor con gradiente. Power BI Desktop debe recargar el proyecto tras ejecutar."""
import json, os, shutil, hashlib, uuid, glob

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PBIR_REPORT_DIR", "modelo.Report")  # carpeta <nombre>.Report del proyecto .pbip
DEF = os.path.join(ROOT, "definition")
PAGES = os.path.join(DEF, "pages")
RR = os.path.join(ROOT, "StaticResources", "RegisteredResources")
VC = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json"
PG = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
W, H = 1280, 720
NAVY, TEAL, ORANGE, GREY, RED, GREEN, BG = "#16324F", "#0F7C8C", "#E07A1F", "#8A99A8", "#C0392B", "#2E8B57", "#F2F4F7"
ACCENTS = [TEAL, ORANGE, "#5B6CC2", RED, GREEN, "#8E44AD"]

# ---------------- tema ----------------
os.makedirs(RR, exist_ok=True)
for f in glob.glob(os.path.join(RR, "HUN2026-*.json")):
    os.remove(f)
theme_name = f"HUN2026-{uuid.uuid4().hex[:10]}.json"
theme = {
    "name": theme_name,
    "dataColors": [TEAL, ORANGE, "#5B6CC2", GREY, RED, GREEN, "#8E44AD", "#D4A017", "#2C3E50", "#7FB3D5"],
    "good": GREEN, "neutral": "#D4A017", "bad": RED,
    "maximum": RED, "center": "#F7DC6F", "minimum": "#EAF4F6",
    "foreground": "#1F2D3D", "background": "#FFFFFF", "tableAccent": TEAL,
    "textClasses": {
        "callout": {"fontSize": 26, "fontFace": "Segoe UI Semibold", "color": "#1F2D3D"},
        "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#1F2D3D"},
        "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#1F2D3D"},
        "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#3B4A5A"}},
    "visualStyles": {
        "*": {"*": {
            "title": [{"show": True, "fontFamily": "Segoe UI Semibold", "fontSize": 12, "fontColor": {"solid": {"color": "#1F2D3D"}}}],
            "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": "#E3E8EE"}}, "radius": 8, "width": 1}],
            "dropShadow": [{"show": True, "color": {"solid": {"color": "#000000"}}, "transparency": 92, "preset": "BottomRight"}],
            "padding": [{"top": 8, "bottom": 8, "left": 10, "right": 10}]}},
        "lineChart": {"*": {"lineStyles": [{"strokeWidth": 3}], "legend": [{"show": True, "position": "Top"}]}},
        "clusteredBarChart": {"*": {"labels": [{"show": True}], "legend": [{"show": True, "position": "Top"}]}},
        "clusteredColumnChart": {"*": {"labels": [{"show": True}], "legend": [{"show": True, "position": "Top"}]}},
        "tableEx": {"*": {"columnHeaders": [{"fontColor": {"solid": {"color": "#FFFFFF"}}, "backColor": {"solid": {"color": NAVY}}}],
                          "values": [{"backColorSecondary": {"solid": {"color": "#F6F8FA"}}}]}},
        "pivotTable": {"*": {"columnHeaders": [{"fontColor": {"solid": {"color": "#FFFFFF"}}, "backColor": {"solid": {"color": NAVY}}}],
                             "rowHeaders": [{"fontColor": {"solid": {"color": "#1F2D3D"}}}]}},
    }}
json.dump(theme, open(os.path.join(RR, theme_name), "w", encoding="utf-8"), indent=2)
rep = json.load(open(os.path.join(DEF, "report.json"), encoding="utf-8"))
ver = rep["themeCollection"]["baseTheme"]["reportVersionAtImport"]
rep["themeCollection"]["customTheme"] = {"name": theme_name, "reportVersionAtImport": ver, "type": "RegisteredResources"}
rep["resourcePackages"] = [p for p in rep["resourcePackages"] if p["type"] != "RegisteredResources"]
rep["resourcePackages"].append({"name": "RegisteredResources", "type": "RegisteredResources",
                                "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}]})
json.dump(rep, open(os.path.join(DEF, "report.json"), "w", encoding="utf-8"), indent=2)


# ---------------- helpers ----------------
def L(v):
    return {"expr": {"Literal": {"Value": v}}}


def S(s):
    return L("'" + str(s).replace("'", "''") + "'")


def color(hexc):
    return {"solid": {"color": S(hexc)}}


def uid(*s):
    return hashlib.md5("|".join(map(str, s)).encode()).hexdigest()[:20]


def meas(n):
    return ({"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": n}}, f"_Medidas.{n}", n)


def col(t, c):
    return ({"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}, f"{t}.{c}", c)


def agg(t, c, fn=0):
    return ({"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}, "Function": fn}},
            f"{'Sum' if fn == 0 else 'Avg'}({t}.{c})", c)


def proj(f, active=False, display=None):
    d = {"field": f[0], "queryRef": f[1], "nativeQueryRef": f[2]}
    if active:
        d["active"] = True
    if display:
        d["displayName"] = display
    return d


def container(page, i, x, y, w, h, visual):
    n = uid(page, i)
    return n, {"$schema": VC, "name": n, "position": {"x": x, "y": y, "z": i * 1000, "height": h, "width": w, "tabOrder": i * 1000}, "visual": visual}


def vco(title=None, subtitle=None, bg=None, border=True, shadow=True):
    o = {}
    if title is not None:
        o["title"] = [{"properties": {"show": L("true"), "text": S(title)}}]
    if subtitle:
        o["subTitle"] = [{"properties": {"show": L("true"), "text": S(subtitle), "fontColor": color("#6B7A89")}}]
    if bg:
        o["background"] = [{"properties": {"show": L("true"), "color": color(bg), "transparency": L("0D")}}]
    if not border:
        o["border"] = [{"properties": {"show": L("false")}}]
    if not shadow:
        o["dropShadow"] = [{"properties": {"show": L("false")}}]
    return o


def chart(page, i, vtype, x, y, w, h, roles, title, subtitle=None, series_colors=None, objects=None, display=None, sort=None):
    display = display or {}
    qs = {r: {"projections": [proj(f, active=(r in ("Category", "Rows")), display=display.get(f[1])) for f in fs]} for r, fs in roles.items()}
    q = {"queryState": qs}
    if sort:
        q["sortDefinition"] = {"sort": [{"field": sort[0][0], "direction": sort[1]}], "isDefaultSort": True}
    v = {"visualType": vtype, "query": q, "drillFilterOtherVisuals": True, "visualContainerObjects": vco(title, subtitle)}
    obj = dict(objects or {})
    if vtype == "tableEx":
        obj.setdefault("total", [{"properties": {"totals": L("false")}}])
        obj.setdefault("values", [{"properties": {"wordWrap": L("true")}}])
    if series_colors:
        obj["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"metadata": qref}} for qref, c in series_colors.items()]
    if obj:
        v["objects"] = obj
    return container(page, i, x, y, w, h, v)


def card(page, i, x, y, w, h, measure, label, accent):
    v = {"visualType": "cardVisual",
         "query": {"queryState": {"Data": {"projections": [proj(meas(measure), display=label)]}}},
         "objects": {
             "accentBar": [{"properties": {"show": L("true"), "position": S("Left"), "width": L("5D"), "color": color(accent)}, "selector": {"id": "default"}}],
             "outline": [{"properties": {"show": L("false")}, "selector": {"id": "default"}}],
             "value": [{"properties": {"fontSize": L("24D"), "fontColor": color("#1F2D3D"), "labelDisplayUnits": L("1D")}, "selector": {"id": "default"}}],
             "label": [{"properties": {"fontSize": L("10D"), "fontColor": color("#6B7A89")}, "selector": {"id": "default"}}]},
         "visualContainerObjects": vco(None) | {"title": [{"properties": {"show": L("false")}}]},
         "drillFilterOtherVisuals": True}
    return container(page, i, x, y, w, h, v)


def text(page, i, x, y, w, h, lines, size=11, bg=None, fg="#1F2D3D", first_bold=True, border=True, shadow=True):
    paras = [{"textRuns": [{"value": ln, "textStyle": {"fontSize": f"{size if k or not first_bold else size + 1}pt", "color": fg,
                                                       **({"fontWeight": "bold"} if (k == 0 and first_bold) else {})}}]} for k, ln in enumerate(lines)]
    v = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paras}}]},
         "visualContainerObjects": vco(None, bg=bg, border=border, shadow=shadow), "drillFilterOtherVisuals": True}
    return container(page, i, x, y, w, h, v)


def header(page, title, subtitle):
    return text(page, 0, 0, 0, W, 64, [title, subtitle], size=10, bg=NAVY, fg="#FFFFFF", border=False, shadow=False)


def kpi_row(page, start, y, items, x0=16, total_w=W - 32, h=92):
    n, gap = len(items), 12
    w = (total_w - gap * (n - 1)) // n
    return [card(page, start + k, x0 + k * (w + gap), y, w, h, m, lab, ACCENTS[k % len(ACCENTS)]) for k, (m, lab) in enumerate(items)]


P = []
INTER = {}
SUB = "Data Challenge HUN 2026 · Equipo DATACHALLENGE_G12 · feb-2023 a abr-2026 · datos agregados"

# ---------- 1. Resumen ----------
p = "p1_resumen"
v = [header(p, "Flujo urgencias → hospitalización: resumen", SUB)]
v += kpi_row(p, 1, 76, [("Mediana h hasta hosp", "Mediana horas a hosp."), ("% ingresados > 24h", "Ingresados > 24 h (real)"),
                        ("Tasa de ingreso", "Tasa de ingreso"), ("Censo hospitalización medio", "Hospitalizados, incl. UCI"),
                        ("% altas antes 12h", "Altas antes 12 h"), ("% horas saturadas", "Horas saturadas (%)")])
km = "f_kpi_mensual"
v.append(chart(p, 10, "lineChart", 16, 182, 820, 522, {"Category": [col(km, "anio_mes")], "Y": [agg(km, "mediana_h_hasta_hosp"), agg(km, "p90_h_hasta_hosp")]},
               "Horas desde la llegada a urgencias hasta la hospitalización", "Pacientes que ingresan · mediana y p90 mensuales · la cola (p90) empeora de ~70 h a ~90 h",
               series_colors={f"Sum({km}.mediana_h_hasta_hosp)": TEAL, f"Sum({km}.p90_h_hasta_hosp)": ORANGE},
               display={f"Sum({km}.mediana_h_hasta_hosp)": "Mediana (h)", f"Sum({km}.p90_h_hasta_hosp)": "Percentil 90 (h)"}))
v.append(text(p, 11, 852, 182, 412, 232, [
    "Lo que muestran los datos",
    "① Cuello de botella: urgencias → hospitalización. Mediana ~23 h (67 % de los ingresados > 12 h). Con la base de Inglaterra (todas las atenciones), 43 % > 12 h frente a ≈ 10 %.",
    "② Solo 13 % de las altas ocurre antes del mediodía; la capacidad efectiva calibrada está al límite (supuesto).",
    "③ Quien llega de día espera ~28 h; de madrugada ~16 h.",
    "④ Interconsultas quirúrgicas: ortopedia +22 h, urología +18 h, cirugía +7 h, ajustando por edad, horario, año, censos y UCI (asociación).",
    "⑤ Altas a.m. + interconsultas rápidas: −7,3 h de mediana con 269 camas efectivas (−1,7 a −2,6 h con más holgura), sin costo."], size=10))
eh1 = "f_espera_hora_dia"
v.append(chart(p, 12, "clusteredColumnChart", 852, 426, 412, 278, {"Category": [col(eh1, "hora_llegada")], "Y": [agg(eh1, "mediana_h_hasta_hosp", 1)]},
               "Llegar de día cuesta más espera", "Mediana de horas a hospitalización por hora de llegada",
               series_colors={f"Avg({eh1}.mediana_h_hasta_hosp)": ORANGE}, objects={"labels": [{"properties": {"show": L("false")}}]},
               display={f"Avg({eh1}.mediana_h_hasta_hosp)": "Mediana (h)"}))
P.append((p, "1 · Resumen", v))

# ---------- 2. Cuellos de botella ----------
p = "p2_cuellos"
v = [header(p, "Cuellos de botella: horario de altas, interconsultas y complejidad", SUB)]
ah = "f_altas_ingresos_hora"
v.append(chart(p, 1, "clusteredColumnChart", 16, 76, 620, 310, {"Category": [col(ah, "hora")], "Y": [agg(ah, "altas_hosp"), agg(ah, "ingresos_hosp")]},
               "Las camas se liberan por la tarde; los ingresos llegan de noche", "Altas e ingresos a hospitalización por hora del día (2023-2026)",
               series_colors={f"Sum({ah}.altas_hosp)": TEAL, f"Sum({ah}.ingresos_hosp)": ORANGE},
               objects={"labels": [{"properties": {"show": L("false")}}]},
               display={f"Sum({ah}.altas_hosp)": "Altas", f"Sum({ah}.ingresos_hosp)": "Ingresos"}))
eh = "f_espera_hora_dia"
qref = f"Sum({eh}.mediana_h_hasta_hosp)"
grad = {"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
    "Input": {"SelectRef": {"ExpressionName": qref}},
    "FillRule": {"linearGradient2": {"min": {"color": {"Literal": {"Value": "'#EAF4F6'"}}}, "max": {"color": {"Literal": {"Value": f"'{RED}'"}}},
                                     "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}}}}}}}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": qref}}
v.append(chart(p, 2, "pivotTable", 652, 76, 612, 310, {"Rows": [col(eh, "hora_llegada")], "Columns": [col(eh, "dia_semana_num")], "Values": [agg(eh, "mediana_h_hasta_hosp")]},
               "Mapa de calor: horas hasta hospitalización", "Hora de llegada (filas) × día de la semana (1 = lunes) · rojo = más espera",
               objects={"values": [grad, {"properties": {"fontSize": L("8D")}}], "grid": [{"properties": {"rowPadding": L("0D")}}], "rowHeaders": [{"properties": {"fontSize": L("8D")}}], "subTotals": [{"properties": {"rowSubtotals": L("false"), "columnSubtotals": L("false")}}]},
               display={qref: "Mediana h"}))
ic = "f_interconsultas"
v.append(chart(p, 3, "clusteredBarChart", 16, 398, 620, 306, {"Category": [col(ic, "servicio")], "Y": [agg(ic, "mediana_h_con"), agg(ic, "mediana_h_sin")]},
               "Interconsultas quirúrgicas: las que más retrasan el ingreso", "Mediana de horas hasta hospitalización con y sin cada interconsulta",
               series_colors={f"Sum({ic}.mediana_h_con)": RED, f"Sum({ic}.mediana_h_sin)": GREY},
               display={f"Sum({ic}.mediana_h_con)": "Con interconsulta", f"Sum({ic}.mediana_h_sin)": "Sin interconsulta"},
               sort=(agg(ic, "mediana_h_con"), "Descending")))
ns = "f_n_servicios"
v.append(chart(p, 4, "clusteredColumnChart", 652, 398, 612, 306, {"Category": [col(ns, "n_servicios")], "Y": [agg(ns, "mediana_h_hasta_hosp"), agg(ns, "p90_h")]},
               "Más servicios involucrados ⇒ más espera", "Horas a hospitalización por número de servicios (5 = 5 o más)",
               series_colors={f"Sum({ns}.mediana_h_hasta_hosp)": TEAL, f"Sum({ns}.p90_h)": "#7FB3D5"},
               display={f"Sum({ns}.mediana_h_hasta_hosp)": "Mediana (h)", f"Sum({ns}.p90_h)": "Percentil 90 (h)"}))
P.append((p, "2 · Cuellos de botella", v))

# ---------- 3. Congestion ----------
p = "p3_congestion"
v = [header(p, "Congestión y alerta temprana", "Umbral de saturación: 287 pacientes simultáneos en urgencias (p90 histórico 2023-2024) · " + SUB)]
v += kpi_row(p, 1, 76, [("Censo urgencias medio", "Pacientes en urgencias (media)"), ("Horas saturadas", "Horas saturadas"),
                        ("Precisión alerta 3h", "Precisión alerta 3 h (IC 0,71–0,87)"), ("Recall alerta 3h", "Recall 3 h (IC 0,53–0,73)")], total_w=1040)
v.append(chart(p, 5, "slicer", 1068, 76, 196, 92, {"Values": [col("dim_fecha", "anio")]}, "Año", None,
               objects={"data": [{"properties": {"mode": S("Dropdown")}}], "header": [{"properties": {"show": L("false")}}]}))
v.append(chart(p, 6, "lineChart", 16, 182, 1248, 250, {"Category": [col("dim_fecha", "fecha")], "Y": [meas("Censo urgencias medio"), meas("Censo hospitalización medio")]},
               "Ocupación diaria: urgencias y hospitalización", "Censo medio por día · la hospitalización se mantiene en su techo; urgencias absorbe la presión",
               series_colors={"_Medidas.Censo urgencias medio": ORANGE, "_Medidas.Censo hospitalización medio": TEAL},
               objects={"lineStyles": [{"properties": {"strokeWidth": L("2D")}}]}))
pr = "f_pronostico_3h"
refline = [{"properties": {"show": L("true"), "displayName": S("Umbral de saturación (287)"), "value": L("287D"), "lineColor": color(RED),
                           "style": S("dashed"), "width": L("2D"), "dataLabelShow": L("true"), "dataLabelColor": color(RED)}, "selector": {"id": "1"}}]
v.append(chart(p, 7, "lineChart", 16, 444, 1248, 260, {"Category": [col(pr, "fecha_hora_objetivo")], "Y": [agg(pr, "censo_real"), agg(pr, "censo_pronosticado_3h")]},
               "La alerta funciona: pronóstico hecho 3 h antes vs censo real", "Periodo de prueba ene-abr 2026 (no usado para entrenar) · LightGBM vs persistencia: MAE 16,3 vs 22,6",
               series_colors={f"Sum({pr}.censo_real)": NAVY, f"Sum({pr}.censo_pronosticado_3h)": ORANGE},
               objects={"y1AxisReferenceLine": refline, "lineStyles": [{"properties": {"strokeWidth": L("1.5D")}}]},
               display={f"Sum({pr}.censo_real)": "Censo real", f"Sum({pr}.censo_pronosticado_3h)": "Pronóstico a 3 h"}))
P.append((p, "3 · Congestión y alerta", v))

# ---------- 4. Simulacion ----------
p = "p4_simulacion"
v = [header(p, "Optimización: ¿cuánto se gana sin invertir?", "Simulación de eventos discretos calibrada con 2025 (C = 269 camas efectivas, 30 réplicas) · " + SUB)]
v += kpi_row(p, 1, 76, [("Δ mediana escenario (h)", "Δ mediana del escenario, horas"),
                        ("Δ p90 escenario (h)", "Δ percentil 90, horas"),
                        ("Horas-paciente ahorradas al año", "Horas-paciente ahorradas/año")], total_w=820)
v.append(chart(p, 7, "slicer", 852, 76, 412, 92, {"Values": [col("f_simulacion_escenarios", "escenario")]},
               "Escenario (sin selección = combinado 50 % / −50 %)", None,
               objects={"data": [{"properties": {"mode": S("Dropdown")}}], "header": [{"properties": {"show": L("false")}}]}))
INTER["p4_simulacion"] = [(uid(p, 7), uid(p, 4)), (uid(p, 7), uid(p, 6))]
se = "f_simulacion_escenarios"
v.append(chart(p, 4, "clusteredBarChart", 16, 182, 620, 522, {"Category": [col(se, "escenario")], "Y": [agg(se, "delta_mediana_h"), agg(se, "delta_p90_h")]},
               "Mejora por escenario (horas; negativo = menos espera)", "Con 269 camas calibradas; con más holgura, combinado −2,6 h (279) o −1,7 h (289)",
               series_colors={f"Sum({se}.delta_mediana_h)": TEAL, f"Sum({se}.delta_p90_h)": ORANGE},
               display={f"Sum({se}.delta_mediana_h)": "Δ mediana (h)", f"Sum({se}.delta_p90_h)": "Δ p90 (h)"},
               sort=(agg(se, "delta_p90_h"), "Ascending")))
ss = "f_simulacion_sensibilidad"
v.append(chart(p, 5, "lineChart", 652, 182, 612, 250, {"Category": [col(ss, "C")], "Y": [agg(ss, "delta_altas_am_30pct", 1), agg(ss, "delta_interconsulta_quir_-50pct", 1)]},
               "El hospital opera en el filo de su capacidad", "Δ mediana (h) según las camas supuestas; bajo ~260 la cola es inestable",
               series_colors={f"Avg({ss}.delta_altas_am_30pct)": TEAL, f"Avg({ss}.delta_interconsulta_quir_-50pct)": RED},
               objects={"valueAxis": [{"properties": {"start": L("-20D"), "end": L("0D")}}]},
               display={f"Avg({ss}.delta_altas_am_30pct)": "Altas a.m. 30 %", f"Avg({ss}.delta_interconsulta_quir_-50pct)": "Interconsultas −50 %"}))
v.append(chart(p, 6, "tableEx", 652, 444, 612, 260, {"Values": [col(se, "escenario"), agg(se, "mediana_h"), agg(se, "pct_mas24h"), agg(se, "horas_paciente_ahorradas_anio")]},
               "Resultados por escenario", None, objects={"values": [{"properties": {"wordWrap": L("true"), "fontSize": L("9D")}}], "columnHeaders": [{"properties": {"fontSize": L("9D")}}]},
               display={f"Sum({se}.mediana_h)": "Mediana (h)", f"Sum({se}.pct_mas24h)": "% > 24 h", f"Sum({se}.horas_paciente_ahorradas_anio)": "Horas-paciente ahorradas/año"}))
P.append((p, "4 · Mejoras (simulación)", v))

# ---------- 5. Flujo y modelos ----------
p = "p5_flujo"
v = [header(p, "Flujo entre etapas, perfil de pacientes y modelo predictivo", SUB)]
ft = "f_flujo_transiciones"
v.append(chart(p, 1, "hundredPercentStackedBarChart", 16, 76, 620, 300, {"Category": [col(ft, "origen")], "Series": [col(ft, "destino")], "Y": [agg(ft, "n")]},
               "Flujo entre etapas: a dónde pasa cada etapa (% de episodios)", "Registro (4 min) → atención en urgencias (13 h) → hospitalización",
               display={f"Sum({ft}.n)": "Episodios"}))
ed = "f_edad"
v.append(chart(p, 2, "clusteredColumnChart", 652, 76, 612, 300, {"Category": [col(ed, "grupo_edad")], "Y": [agg(ed, "tasa_ingreso_pct")]},
               "Los mayores ingresan más", "Tasa de ingreso (%) desde urgencias por grupo de edad",
               series_colors={f"Sum({ed}.tasa_ingreso_pct)": "#5B6CC2"}, display={f"Sum({ed}.tasa_ingreso_pct)": "Tasa de ingreso (%)"}))
md = "f_modelo_ingreso_deciles"
v.append(chart(p, 3, "clusteredColumnChart", 16, 388, 620, 316, {"Category": [col(md, "decil_riesgo")], "Y": [agg(md, "tasa_ingreso_real")]},
               "Modelo de ingreso a las 3 h (AUC 0,71; IC 0,70–0,72): ordena bien el riesgo", "Proporción real de ingresos por decil de riesgo predicho (prueba ene-abr 2026)",
               series_colors={f"Sum({md}.tasa_ingreso_real)": TEAL}, display={f"Sum({md}.tasa_ingreso_real)": "Proporción que ingresa"}))
cd = "f_calidad_datos"
v.append(chart(p, 4, "tableEx", 652, 388, 612, 316, {"Values": [col(cd, "problema"), col(cd, "alcance"), col(cd, "tratamiento")]},
               "Calidad de datos y tratamiento", "Supuestos S1–S5 en el documento (sección 2.2)",
               objects={"columnWidth": [{"properties": {"value": L(f"{w}D")}, "selector": {"metadata": f"{cd}.{c}"}} for c, w in (("problema", 205), ("alcance", 140), ("tratamiento", 225))],
                        "columnHeaders": [{"properties": {"autoSizeColumnWidth": L("false"), "wordWrap": L("true")}}],
                        "values": [{"properties": {"wordWrap": L("true"), "fontSize": L("9D")}}]}))
P.append((p, "5 · Flujo, modelos y datos", v))

# ---------- 6. Rigor y robustez ----------
p = "p6_rigor"
v = [header(p, "Rigor y robustez: ¿cuánto podemos confiar en los resultados?", "Efecto ajustado, modelo predictivo, análisis de decisión y validación fuera de muestra · " + SUB)]
v += kpi_row(p, 1, 76, [("Ingresos anticipados por día", "Ingresos anticipados/día (top 20 % de riesgo)"),
                        ("Horas de antelación (mediana)", "Horas de antelación (mediana)"),
                        ("AUC modelo ingreso 3h", "AUC del modelo a las 3 h")])
ia = "f_interconsultas_ajustado"
v.append(chart(p, 5, "clusteredBarChart", 16, 182, 620, 522, {"Category": [col(ia, "servicio")], "Y": [agg(ia, "crudo_h"), agg(ia, "ajustado_h")]},
               "Las interconsultas quirúrgicas siguen pesando al ajustar", "Δ horas crudo vs ajustado (regresión cuantil); «nota» y «examen» = genéricos",
               series_colors={f"Sum({ia}.crudo_h)": GREY, f"Sum({ia}.ajustado_h)": RED},
               display={f"Sum({ia}.crudo_h)": "Crudo (h)", f"Sum({ia}.ajustado_h)": "Ajustado (h)"}, sort=(agg(ia, "ajustado_h"), "Descending")))
mv = "f_modelo_ventanas"
v.append(chart(p, 6, "clusteredColumnChart", 652, 182, 612, 250, {"Category": [col(mv, "modelo")], "Y": [agg(mv, "auc")]},
               "Más información, mejor predicción (AUC en prueba 2026)", "Eje desde 0,5 (azar) · LightGBM a 1, 3 y 6 h vs logística a 3 h",
               series_colors={f"Sum({mv}.auc)": TEAL}, display={f"Sum({mv}.auc)": "AUC"}, sort=(agg(mv, "orden"), "Ascending"),
               objects={"valueAxis": [{"properties": {"start": L("0.5D"), "end": L("0.75D")}}]}))
vl = "f_validacion_2026"
v.append(chart(p, 7, "tableEx", 652, 444, 612, 260, {"Values": [col(vl, "indicador"), agg(vl, "observado_2026"), agg(vl, "simulado_C269"), agg(vl, "simulado_C260")]},
               "Validación fuera de muestra (ene-mar 2026)", "Se sostiene el orden de las medidas, no los valores absolutos",
               display={f"Sum({vl}.observado_2026)": "Observado 2026", f"Sum({vl}.simulado_C269)": "Simulado (C=269)", f"Sum({vl}.simulado_C260)": "Simulado (C=260)"}))
P.append((p, "6 · Rigor y robustez", v))

# ---------- 7. Seguimiento del piloto ----------
p = "p7_piloto"
v = [header(p, "Seguimiento del piloto: ¿se están adelantando las altas?", "Tablero semanal propuesto para el piloto de 6 semanas (medidas 1 y 3) · elegir el año para comparar · " + SUB)]
v += kpi_row(p, 1, 76, [("% altas antes 12h", "Altas antes de las 12 h"), ("Meta altas antes 12h", "Meta del piloto"),
                        ("% horas saturadas", "Horas con urgencias saturada"), ("Censo urgencias medio", "Pacientes en urgencias (media)")], total_w=1040)
v.append(chart(p, 5, "slicer", 1068, 76, 196, 92, {"Values": [col("dim_fecha", "anio")]}, "Año", None,
               objects={"data": [{"properties": {"mode": S("Dropdown")}}], "header": [{"properties": {"show": L("false")}}]}))
v.append(chart(p, 6, "lineChart", 16, 182, 620, 260, {"Category": [col("dim_fecha", "anio_mes")], "Y": [meas("% altas antes 12h"), meas("Meta altas antes 12h")]},
               "KPI 1 · Altas antes del mediodía frente a la meta", "% mensual de altas de hospitalización antes de las 12 h; meta 30 %",
               series_colors={"_Medidas.% altas antes 12h": TEAL, "_Medidas.Meta altas antes 12h": RED}))
v.append(chart(p, 7, "lineChart", 652, 182, 612, 260, {"Category": [col("dim_fecha", "anio_mes")], "Y": [meas("% horas saturadas")]},
               "KPI 2 · Horas con urgencias saturada", "% mensual de horas con más de 287 pacientes en urgencias",
               series_colors={"_Medidas.% horas saturadas": ORANGE}))
v.append(chart(p, 8, "clusteredColumnChart", 16, 454, 1248, 250, {"Category": [col("f_hora", "hora")], "Y": [meas("Altas"), meas("Ingresos a hospitalización")]},
               "KPI 3 · ¿Se mueve la ola de altas hacia la mañana?", "Altas e ingresos a hospitalización por hora del día (según el año elegido); el objetivo es adelantar la ola de las 15–18 h",
               series_colors={"_Medidas.Altas": TEAL, "_Medidas.Ingresos a hospitalización": ORANGE}, objects={"labels": [{"properties": {"show": L("false")}}]}))
P.append((p, "7 · Seguimiento del piloto", v))

# ---------------- escribir ----------------
for d in os.listdir(PAGES):
    if os.path.isdir(os.path.join(PAGES, d)):
        shutil.rmtree(os.path.join(PAGES, d))
order = []
for pid, disp, vis in P:
    pdir = os.path.join(PAGES, pid)
    os.makedirs(os.path.join(pdir, "visuals"))
    page = {"$schema": PG, "name": pid, "displayName": disp, "displayOption": "FitToPage", "height": H, "width": W,
            "objects": {"background": [{"properties": {"color": color(BG), "transparency": L("0D")}}]}}
    if pid in INTER:
        page["visualInteractions"] = [{"source": a, "target": b, "type": "NoFilter"} for a, b in INTER[pid]]
    json.dump(page, open(os.path.join(pdir, "page.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for n, body in vis:
        os.makedirs(os.path.join(pdir, "visuals", n))
        json.dump(body, open(os.path.join(pdir, "visuals", n, "visual.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    order.append(pid)
json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
           "pageOrder": order, "activePageName": order[0]}, open(os.path.join(PAGES, "pages.json"), "w", encoding="utf-8"), indent=2)
print("tema:", theme_name, "| paginas:", len(P), "| visuales:", sum(len(x[2]) for x in P))
