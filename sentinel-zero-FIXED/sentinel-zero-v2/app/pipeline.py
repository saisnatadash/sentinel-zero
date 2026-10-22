"""Detection and validation pipeline.

Steps: classify text (English, Hindi, Odia) -> remove duplicates -> keep relevant categories
-> spatio-temporal clustering -> anomaly vs baseline -> evidence and contradiction checks
-> score -> explain. See docs/methodology.md.
"""
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

import numpy as np
from sklearn.cluster import DBSCAN

from .lang import classify, has_negation
from .models import AnalysisRequest, LabResult, Report
from .risk_engine import CONTRADICTION_CAP_SHARE, MIN_INDEPENDENT_SOURCES, score_cluster

EPS = 2.5
TIME_WEIGHT = 0.25
MIN_SAMPLES = 4
DUP_WINDOW = timedelta(hours=48)
DUP_SIMILARITY = 0.9
LAB_MATCH_WINDOW = timedelta(days=3)
RELEVANT_CATEGORIES = {"water_odour", "water_colour", "diarrhoea_symptoms"}
WATER_CATEGORIES = {"water_odour", "water_colour"}
ASCII_PUNCTUATION = re.compile(r"[!-/:-@\[-`{-~]")  # keeps Hindi and Odia letters intact
COORDINATE_DECIMALS = 2  # about 1 km: enough for a cluster, not enough to locate a household
DISCLAIMER = (
    "Prototype output for human review. It flags patterns, not confirmed outbreaks, "
    "and does not certify water safety."
)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def normalise(text: str) -> str:
    return " ".join(ASCII_PUNCTUATION.sub(" ", text.lower()).split())


def is_contradictory(report: Report) -> bool:
    return report.category in WATER_CATEGORIES and has_negation(report.text)


def _with_category(report: Report) -> Report:
    if report.category != "other":
        return report
    category = classify(report.text)
    return report.model_copy(update={"category": category}) if category != "other" else report


def remove_duplicates(reports: list[Report]) -> tuple[list[Report], list[dict]]:
    kept: list[Report] = []
    duplicates: list[dict] = []
    for r in sorted(reports, key=lambda x: x.timestamp):
        key = normalise(r.text)
        original = None
        for k in kept:
            if (
                k.source_id == r.source_id
                and k.locality == r.locality
                and abs(r.timestamp - k.timestamp) <= DUP_WINDOW
                and SequenceMatcher(None, key, normalise(k.text)).ratio() >= DUP_SIMILARITY
            ):
                original = k.id
                break
        if original:
            duplicates.append({"duplicate_id": r.id, "duplicate_of": original,
                               "reason": "same source, near-identical text"})
        else:
            kept.append(r)
    return kept, duplicates


def cluster_reports(reports: list[Report]) -> list[list[Report]]:
    if len(reports) < MIN_SAMPLES:
        return []
    lat0 = sum(r.lat for r in reports) / len(reports)
    lon0 = sum(r.lon for r in reports) / len(reports)
    t0 = min(r.timestamp for r in reports)
    coords = np.array([
        [
            (r.lon - lon0) * 111 * math.cos(math.radians(lat0)),
            (r.lat - lat0) * 111,
            (r.timestamp - t0).total_seconds() / 3600 * TIME_WEIGHT,
        ]
        for r in reports
    ])
    labels = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES).fit_predict(coords)
    groups: dict[int, list[Report]] = defaultdict(list)
    for report, label in zip(reports, labels):
        if label >= 0:
            groups[label].append(report)
    return [groups[k] for k in sorted(groups)]


def _matching_labs(labs: list[LabResult], locality: str, start: datetime, end: datetime) -> list[LabResult]:
    return [
        lab for lab in labs
        if lab.locality == locality and start - LAB_MATCH_WINDOW <= lab.timestamp <= end + LAB_MATCH_WINDOW
    ]


def _alternatives(*, events, negative, forwarded, sources, anomaly, contradiction_share, evidence) -> list[str]:
    alts = []
    if events:
        alts.append(f"{len(events)} report(s) mention a community event ({', '.join(sorted(set(events)))}), "
                    "which may explain the symptoms.")
    if negative:
        alts.append("Laboratory tests for the relevant agent were negative in this locality.")
    if forwarded:
        alts.append("Identical wording appears across sources, which may indicate a forwarded message.")
    if sources < MIN_INDEPENDENT_SOURCES:
        alts.append("Too few independent sources; reports may come from one person or coordinated posting.")
    if anomaly < 0.4:
        alts.append("Report volume is close to this locality's normal background level.")
    if contradiction_share >= CONTRADICTION_CAP_SHARE:
        alts.append("Reports disagree about the water's condition.")
    if evidence == 0.3:
        alts.append("No laboratory or official evidence is available yet.")
    if not alts:
        alts.append("The rules found no obvious alternative explanation; human review is still required.")
    return alts


def _verification_steps(category: str, events: list[str], evidence: float) -> list[str]:
    steps = []
    if category in WATER_CATEGORIES:
        steps.append("Collect water samples from the source, storage tank and household taps for bacteriological testing.")
    if category == "diarrhoea_symptoms":
        steps.append("Check recent admissions at nearby health facilities against the locality's usual pattern.")
    steps.append("Ask the local water utility whether there was a supply disruption, pipe repair or tanker change in this window.")
    if events:
        steps.append("Check whether a community event took place and what food or water was shared.")
    if evidence == 0.3:
        steps.append("Request official surveillance data for the area and period.")
    return steps


def _what_would_change(evidence: float) -> list[str]:
    items = ["A negative laboratory result for the relevant agent in this locality would cap this cluster at Watch.",
             "A confirmed water-supply repair or tanker change covering this window would offer a simpler explanation.",
             "Evidence that the reports come from one source or a forwarded message would lower independence."]
    if evidence != 1.0:
        items.append("A positive laboratory result in this locality would raise the evidence factor.")
    return items


def _build_cluster(members, relevant, labs, span_days) -> dict:
    members = sorted(members, key=lambda r: r.timestamp)
    n = len(members)
    sources = {m.source_id for m in members}
    k = len(sources)
    locality = Counter(m.locality for m in members).most_common(1)[0][0]
    category = Counter(m.category for m in members).most_common(1)[0][0]
    start, end = members[0].timestamp, members[-1].timestamp
    window_hours = max((end - start).total_seconds() / 3600, 1.0)

    seen: dict[str, str] = {}
    forwarded = 0
    for m in members:
        key = normalise(m.text)
        if key in seen and seen[key] != m.source_id:
            forwarded += 1
        else:
            seen.setdefault(key, m.source_id)
    independence = clamp((k - 0.5 * forwarded) / n)

    contradiction_share = sum(is_contradictory(m) for m in members) / n
    consistency = 1 - contradiction_share

    member_ids = {m.id for m in members}
    background = sum(1 for r in relevant
                     if r.locality == locality and r.category == category and r.id not in member_ids)
    expected = max(background / span_days * (window_hours / 24), 0.5)
    z = (n - expected) / math.sqrt(expected)
    anomaly = clamp(z / 5)

    lab_hits = _matching_labs(labs, locality, start, end)
    positive = any(lab.result == "positive" for lab in lab_hits)
    negative = any(lab.result == "negative" for lab in lab_hits) and not positive
    evidence = 1.0 if positive else 0.0 if negative else 0.3

    scored = score_cluster(anomaly=anomaly, independence=independence, evidence=evidence,
                           consistency=consistency, distinct_sources=k,
                           contradiction_share=contradiction_share, lab_negative=negative)
    events = [m.event_flag for m in members if m.event_flag]
    centroid = {"lat": round(sum(m.lat for m in members) / n, COORDINATE_DECIMALS),
                "lon": round(sum(m.lon for m in members) / n, COORDINATE_DECIMALS)}
    explanation = (
        f"{n} reports from {k} independent source(s) in {locality} over {window_hours:.0f} hours. "
        f"Anomaly {scored['factors']['anomaly']:.2f} against baseline; "
        f"laboratory evidence {'positive' if positive else 'negative' if negative else 'not available'}."
    )
    return {
        "locality": locality,
        "category": category,
        "report_count": n,
        "distinct_sources": k,
        "forwarded_reports": forwarded,
        "window_hours": round(window_hours, 1),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "centroid": centroid,
        "tier": scored["tier"],
        "confidence": scored["confidence"],
        "factors": scored["factors"],
        "caps": scored["caps"],
        "explanation": explanation,
        "alternative_explanations": _alternatives(
            events=events, negative=negative, forwarded=forwarded, sources=k,
            anomaly=anomaly, contradiction_share=contradiction_share, evidence=evidence),
        "what_would_change_verdict": _what_would_change(evidence),
        "verification_steps": _verification_steps(category, events, evidence),
        "report_ids": [m.id for m in members],
    }


def analyse(req: AnalysisRequest) -> dict:
    all_reports = [_with_category(r) for r in req.reports]
    kept, duplicates = remove_duplicates(all_reports)
    relevant = [r for r in kept if r.category in RELEVANT_CATEGORIES]
    groups = cluster_reports(relevant)

    if all_reports:
        t_min = min(r.timestamp for r in all_reports)
        t_max = max(r.timestamp for r in all_reports)
        span_days = max((t_max - t_min).total_seconds() / 86400, 1.0)
    else:
        span_days = 1.0

    clusters = [_build_cluster(g, relevant, req.lab_results, span_days) for g in groups]
    clusters.sort(key=lambda c: c["confidence"], reverse=True)
    for i, c in enumerate(clusters, 1):
        c["cluster_id"] = f"C{i}"

    tiers = Counter(c["tier"] for c in clusters)
    return {
        "summary": {
            "total_reports": len(all_reports),
            "duplicates_removed": len(duplicates),
            "relevant_reports": len(relevant),
            "clusters": len(clusters),
            "investigate_count": tiers.get("Investigate", 0),
            "watch_count": tiers.get("Watch", 0),
            "insufficient_count": tiers.get("Insufficient evidence", 0),
            "disclaimer": DISCLAIMER,
        },
        "duplicates": duplicates,
        "clusters": clusters,
    }
