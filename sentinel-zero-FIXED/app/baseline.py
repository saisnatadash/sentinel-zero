"""A deliberately simple comparison rule.

Alert when any locality receives five or more relevant reports within 24 hours.
It has no de-duplication, no source-independence check and no evidence check.
It exists only so that SENTINEL ZERO can be measured against a plain alternative.
"""
from datetime import timedelta

from .lang import classify
from .models import AnalysisRequest

THRESHOLD = 5
WINDOW = timedelta(hours=24)
RELEVANT = {"water_odour", "water_colour", "diarrhoea_symptoms"}


def baseline_alerts(req: AnalysisRequest) -> list[dict]:
    by_locality: dict[str, list] = {}
    for r in req.reports:
        category = r.category if r.category != "other" else classify(r.text)
        if category in RELEVANT:
            by_locality.setdefault(r.locality, []).append(r.timestamp)

    alerts = []
    for locality, times in by_locality.items():
        times.sort()
        for i, start in enumerate(times):
            count = sum(1 for t in times[i:] if t - start <= WINDOW)
            if count >= THRESHOLD:
                alerts.append({"locality": locality, "reports_in_24h": count, "first_alert": start.isoformat()})
                break
    return alerts
