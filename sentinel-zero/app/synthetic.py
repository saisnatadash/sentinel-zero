"""Deterministic SYNTHETIC scenarios for demonstrating the pipeline.

Nothing generated here represents a real incident. Coordinates are approximate town centres
used only to make the map readable. Run `python -m app.synthetic` to regenerate data/*.csv.
"""
import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from .models import AnalysisRequest, LabResult, Report

BASE_TIME = datetime(2026, 9, 1, 6, 0)

LOCALITIES = {
    "Jajpur": (20.85, 86.33),
    "Bhubaneswar": (20.30, 85.82),
    "Cuttack": (20.46, 85.88),
    "Puri": (19.81, 85.83),
    "Balasore": (21.49, 86.91),
    "Berhampur": (19.31, 84.79),
}

TEXTS = {
    "water_odour": [
        "water smells bad near our tap",
        "tap water has a strange smell",
        "rotten smell from the water supply since morning",
        "water smells like sewage",
    ],
    "water_colour": ["water looks yellowish from the tap", "brown water coming from the pipe"],
    "diarrhoea_symptoms": ["several people in our lane have loose motions", "stomach upset after drinking tap water"],
    "other": ["bus fare increased again", "power cut for two hours yesterday", "school timings changed this week"],
}


def _point(rng: random.Random, locality: str, spread_km: float = 1.0) -> tuple[float, float]:
    lat, lon = LOCALITIES[locality]
    dlat = rng.uniform(-spread_km, spread_km) / 111.0
    dlon = rng.uniform(-spread_km, spread_km) / (111.0 * math.cos(math.radians(lat)))
    return round(lat + dlat, 5), round(lon + dlon, 5)


def _report(rng, rid, locality, category, text, hours, source, event_flag=None) -> Report:
    lat, lon = _point(rng, locality)
    return Report(
        id=rid, text=text, lat=lat, lon=lon,
        timestamp=BASE_TIME + timedelta(hours=hours),
        locality=locality, source_id=source, category=category, event_flag=event_flag,
    )


def _lab(lid: str, locality: str, hours: float, result: str, agent: str) -> LabResult:
    lat, lon = LOCALITIES[locality]
    return LabResult(
        id=lid, locality=locality, lat=lat, lon=lon,
        timestamp=BASE_TIME + timedelta(hours=hours), result=result, agent=agent,
    )


def _background(rng: random.Random, prefix: str, n: int = 40) -> list[Report]:
    """Unrelated reports across all localities over 14 days. Mostly off-topic; few water complaints."""
    reports = []
    for i in range(n):
        locality = rng.choice(list(LOCALITIES))
        category = rng.choices(
            ["other", "water_odour", "water_colour", "diarrhoea_symptoms"], weights=[85, 5, 5, 5]
        )[0]
        reports.append(
            _report(rng, f"{prefix}-B{i:03d}", locality, category, rng.choice(TEXTS[category]),
                    rng.uniform(0, 14 * 24), f"{prefix}-bg{i:03d}")
        )
    return reports


def _normal(rng):
    return _background(rng, "N"), []


def _true_cluster(rng):
    reports = _background(rng, "T")
    for i in range(14):
        category = rng.choice(["water_odour", "diarrhoea_symptoms"])
        reports.append(
            _report(rng, f"T-C{i:02d}", "Jajpur", category, rng.choice(TEXTS[category]),
                    rng.uniform(20, 44), f"T-src{i:02d}")
        )
    return reports, [_lab("T-LAB1", "Jajpur", 36, "positive", "Vibrio cholerae (synthetic)")]


def _duplicates(rng):
    reports = _background(rng, "D")
    viral = "water smells bad near our tap"
    for i in range(12):
        reports.append(_report(rng, f"D-V{i:02d}", "Puri", "water_odour", viral, 50 + i * 0.4, "D-viral-account"))
    reports.append(_report(rng, "D-G1", "Puri", "water_odour", "tap water has a strange smell", 52, "D-src-a"))
    reports.append(_report(rng, "D-G2", "Puri", "water_odour",
                           "rotten smell from the water supply since morning", 53, "D-src-b"))
    return reports, []


def _contradictory(rng):
    reports = _background(rng, "C")
    for i in range(10):
        text = "water smells bad near our tap" if i % 2 == 0 else "water is clear today and has no smell"
        reports.append(_report(rng, f"C-X{i:02d}", "Balasore", "water_odour", text, 60 + i * 1.5, f"C-src{i:02d}"))
    return reports, []


def _coincidental(rng):
    reports = _background(rng, "F")
    for i in range(8):
        reports.append(
            _report(rng, f"F-E{i:02d}", "Cuttack", "diarrhoea_symptoms", rng.choice(TEXTS["diarrhoea_symptoms"]),
                    80 + i * 2.2, f"F-src{i:02d}", event_flag="community_feast")
        )
    return reports, [_lab("F-LAB1", "Cuttack", 84, "negative", "Vibrio cholerae (synthetic)")]


SCENARIOS = {
    "normal": {
        "label": "1 · Normal background",
        "description": "Scattered, unrelated reports across six localities.",
        "expected": "No cluster should reach Investigate.",
        "builder": _normal,
    },
    "true_cluster": {
        "label": "2 · Genuine-style cluster",
        "description": "14 water and symptom reports from 14 people in Jajpur within 30 hours, plus a positive lab result.",
        "expected": "Flagged for Investigate.",
        "builder": _true_cluster,
    },
    "duplicates": {
        "label": "3 · Copy-paste flood",
        "description": "One account posts the same message 12 times. Two other people report different issues.",
        "expected": "11 duplicates removed; no cluster forms.",
        "builder": _duplicates,
    },
    "contradictory": {
        "label": "4 · Contradictory reports",
        "description": "10 reports in Balasore: half say the water smells, half say it is clear. No lab result.",
        "expected": "Capped at Watch because the reports contradict each other.",
        "builder": _contradictory,
    },
    "coincidental": {
        "label": "5 · Feast, not water",
        "description": "8 stomach-upset reports in Cuttack after a community feast. The lab test is negative.",
        "expected": "Capped at Watch, with alternative explanations shown.",
        "builder": _coincidental,
    },
}


def build_scenario(name: str, seed: int = 42) -> AnalysisRequest:
    if name not in SCENARIOS:
        raise KeyError(name)
    reports, labs = SCENARIOS[name]["builder"](random.Random(seed))
    return AnalysisRequest(reports=reports, lab_results=labs)


def export_csv(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "sample_reports.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "id", "timestamp", "locality", "lat", "lon", "source_id", "category", "event_flag", "text"])
        for name in SCENARIOS:
            for r in build_scenario(name).reports:
                w.writerow([name, r.id, r.timestamp.isoformat(), r.locality, r.lat, r.lon,
                            r.source_id, r.category, r.event_flag or "", r.text])
    with open(out_dir / "sample_labs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "id", "timestamp", "locality", "lat", "lon", "result", "agent"])
        for name in SCENARIOS:
            for lab in build_scenario(name).lab_results:
                w.writerow([name, lab.id, lab.timestamp.isoformat(), lab.locality, lab.lat, lab.lon,
                            lab.result, lab.agent])


if __name__ == "__main__":
    export_csv(Path(__file__).resolve().parent.parent / "data")
    print("Exported synthetic data to data/")
