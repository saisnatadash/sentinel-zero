"""SYNTHETIC replay of the June 2025 Jajpur diarrhoea timeline.

The daily counts below are scaled-down illustrations shaped by publicly reported milestones:
first cases on 9 June, several hundred affected by 10–11 June, and cholera-positive samples
reported on 14 June. They are NOT case records and must not be presented as such.

The replay tests timing only: on each day, how early does each method raise a flag?
"""
import random
from datetime import datetime, timedelta

from .baseline import baseline_alerts
from .models import AnalysisRequest, LabResult, Report
from .pipeline import analyse

DAY_ZERO = datetime(2025, 6, 9)
DAILY_COUNTS = {9: 1, 10: 14, 11: 10, 12: 10, 13: 8, 14: 6}  # synthetic, keyed by day of June
LOCALITIES = [("Dharmasala", 20.97, 86.22), ("Jajpur", 20.85, 86.33),
              ("Danagadi", 20.72, 86.35), ("Korei", 20.90, 86.20)]
TEXTS = [
    "loose motions after drinking tap water",
    "diarrhoea in our lane, water smells bad",
    "stomach upset, water tastes and smells wrong",
]
MILESTONES = [
    {"date": "2025-06-09", "event": "First case reported in Dharmasala"},
    {"date": "2025-06-10", "event": "Hospital admissions rise; first death reported"},
    {"date": "2025-06-11", "event": "Two deaths reported; hundreds affected"},
    {"date": "2025-06-14", "event": "Cholera-positive samples reported"},
]


def build(seed: int = 7) -> tuple[list[Report], list[LabResult]]:
    rng = random.Random(seed)
    reports: list[Report] = []
    n = 0
    for day, count in DAILY_COUNTS.items():
        for _ in range(count):
            n += 1
            name, lat, lon = LOCALITIES[n % len(LOCALITIES)]
            reports.append(Report(
                id=f"J{n:03d}",
                text=rng.choice(TEXTS),
                lat=round(lat + rng.uniform(-0.01, 0.01), 4),
                lon=round(lon + rng.uniform(-0.01, 0.01), 4),
                timestamp=DAY_ZERO + timedelta(days=day - 9, hours=rng.uniform(0, 22)),
                locality=name,
                source_id=f"J-src{n:03d}",
                category="diarrhoea_symptoms",
            ))
    labs = [LabResult(id="J-LAB", locality="Jajpur", lat=20.85, lon=86.33,
                      timestamp=DAY_ZERO + timedelta(days=5, hours=12),
                      result="positive", agent="Vibrio cholerae (synthetic)")]
    return reports, labs


def run_replay() -> dict:
    reports, labs = build()
    days = []
    for day in sorted(DAILY_COUNTS):
        cutoff = DAY_ZERO + timedelta(days=day - 9, hours=24)
        req = AnalysisRequest(
            reports=[r for r in reports if r.timestamp < cutoff],
            lab_results=[lab for lab in labs if lab.timestamp < cutoff],
        )
        result = analyse(req)
        days.append({
            "date": (DAY_ZERO + timedelta(days=day - 9)).date().isoformat(),
            "reports_to_date": len(req.reports),
            "sentinel_investigate": result["summary"]["investigate_count"],
            "sentinel_watch": result["summary"]["watch_count"],
            "baseline_alerts": len(baseline_alerts(req)),
        })

    def first(key: str):
        return next((d["date"] for d in days if d[key] > 0), None)

    return {
        "label": "Jajpur 2025 timeline replay (synthetic)",
        "disclaimer": "Synthetic counts shaped by reported milestones. This tests timing only. "
                      "It is not case data and does not show that either method would have prevented harm.",
        "milestones": MILESTONES,
        "days": days,
        "first_sentinel_investigate": first("sentinel_investigate"),
        "first_baseline_alert": first("baseline_alerts"),
    }
