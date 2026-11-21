"""Genera un conjunto SINTETICO con el mismo esquema que la extraccion OMOP del reto (sin ningun dato real).

Sirve para probar el pipeline sin acceso a la base del hospital:
    python -m hun.synthetic data/raw_demo --visitas 2000
Reproduce los patrones estructurales encontrados: etapas ER (minutos) -> TRIAGE (horas) -> IP (dias), visitas de
rehabilitacion con duracion 0 y el artefacto de un bloque de etapas ~16 dias antes dentro de la misma visita.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ER, TRIAGE, IP, REHAB = 9203, 3045729, 9201, 581479


def generar(destino: Path, visitas: int = 2000, semilla: int = 0) -> Path:
    rng = np.random.default_rng(semilla)
    destino = Path(destino); destino.mkdir(parents=True, exist_ok=True)
    n_pers = max(50, visitas // 3)
    person = pd.DataFrame({"person_id": np.arange(1, n_pers + 1), "gender_concept_id": rng.choice([8507, 8532], n_pers),
                           "year_of_birth": rng.integers(1935, 2022, n_pers), "race_concept_id": 0, "ethnicity_concept_id": 0})
    t_ini, t_fin = pd.Timestamp("2023-01-01"), pd.Timestamp("2026-04-30")
    span_h = (t_fin - t_ini).total_seconds() / 3600
    vo, vd = [], []
    det_id = 1
    for v in range(1, visitas + 1):
        pid = int(rng.integers(1, n_pers + 1))
        llegada = t_ini + pd.Timedelta(hours=float(rng.uniform(0, span_h)))
        urg = rng.random() < 0.4
        etapas = []
        if urg:
            etapas.append((ER, llegada, llegada + pd.Timedelta(minutes=3)))
            t = etapas[-1][2]
            for _ in range(int(rng.integers(1, 3))):
                fin = t + pd.Timedelta(hours=float(rng.lognormal(1.0, 1.0)))
                etapas.append((TRIAGE, t, fin)); t = fin
            if rng.random() < 0.15:
                etapas.append((IP, t, t + pd.Timedelta(hours=float(rng.lognormal(3.8, 0.8)))))
        else:
            etapas.append((REHAB, llegada, llegada))
        if rng.random() < 0.3:  # artefacto: bloque ~16 dias antes dentro de la misma visita
            previo = llegada - pd.Timedelta(days=float(rng.uniform(15, 19)))
            etapas.insert(0, (REHAB, previo, previo))
        vo.append({"visit_occurrence_id": v, "person_id": pid, "visit_concept_id": ER if urg else REHAB,
                   "visit_start_datetime": llegada, "visit_end_datetime": llegada, "provider_id": 1})
        for c, a, b in etapas:
            vd.append({"visit_detail_id": det_id, "visit_occurrence_id": v, "visit_detail_concept_id": c,
                       "visit_detail_start_datetime": a, "visit_detail_end_datetime": b, "provider_id": 1})
            det_id += 1
    vo, vd = pd.DataFrame(vo), pd.DataFrame(vd)
    concept = pd.DataFrame({"concept_id": [ER, TRIAGE, IP, REHAB, 0, 2006993],
                            "concept_name": ["Emergency Room Visit", "Treatment urgency {Diagnosis}", "Inpatient Visit",
                                             "Ambulatory Rehabilitation Visit", "No matching concept", "Other consultation"],
                            "domain_id": ["Visit", "Measurement", "Visit", "Visit", "Metadata", "Procedure"],
                            "vocabulary_id": ["Visit", "LOINC", "Visit", "Visit", "None", "ICD9Proc"]})
    urg_v = vo[vo.visit_concept_id == ER]
    cond = pd.DataFrame({"condition_occurrence_id": np.arange(1, len(urg_v) + 1), "person_id": urg_v.person_id.values,
                         "visit_occurrence_id": urg_v.visit_occurrence_id.values, "condition_concept_id": 0,
                         "condition_start_datetime": urg_v.visit_start_datetime.values})
    proc = pd.DataFrame({"visit_occurrence_id": urg_v.visit_occurrence_id.values, "person_id": urg_v.person_id.values,
                         "procedure_concept_id": 2006993, "n": 1})
    meas = pd.DataFrame({"measurement_id": np.arange(1, len(urg_v) + 1), "person_id": urg_v.person_id.values,
                         "visit_occurrence_id": urg_v.visit_occurrence_id.values, "measurement_concept_id": 0,
                         "measurement_datetime": urg_v.visit_start_datetime.values + np.timedelta64(90, "m"),
                         "value_as_number": rng.normal(100, 20, len(urg_v))})
    cups = pd.DataFrame({"codigo": ["890201"], "descripcion": ["CONSULTA DE URGENCIAS (sintetico)"], "periodo": ["2021"]})
    for nombre, df in [("person", person), ("visit_occurrence", vo), ("visit_detail", vd), ("concept", concept),
                       ("condition_occurrence", cond), ("procedure_by_visit", proc), ("measurement", meas), ("cups", cups)]:
        df.to_parquet(destino / f"{nombre}.parquet", index=False)
    return destino


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("destino", type=Path)
    ap.add_argument("--visitas", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=0)
    a = ap.parse_args()
    print("Datos sinteticos en", generar(a.destino, a.visitas, a.semilla))
