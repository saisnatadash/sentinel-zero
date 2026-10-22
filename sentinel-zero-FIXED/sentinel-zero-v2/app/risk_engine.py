"""Transparent, rule-based confidence scoring.

Weights and thresholds are deliberately simple so that reviewers can audit every number.
Nothing here is calibrated against real outbreak data; see docs/limitations.md.
"""

WEIGHTS = {"anomaly": 0.35, "independence": 0.25, "evidence": 0.25, "consistency": 0.15}
WATCH_THRESHOLD = 0.35
INVESTIGATE_THRESHOLD = 0.60
MIN_INDEPENDENT_SOURCES = 3
CONTRADICTION_CAP_SHARE = 0.30

INVESTIGATE = "Investigate"
WATCH = "Watch"
INSUFFICIENT = "Insufficient evidence"
_RANK = {INSUFFICIENT: 0, WATCH: 1, INVESTIGATE: 2}


def _tier_for(confidence: float) -> str:
    if confidence >= INVESTIGATE_THRESHOLD:
        return INVESTIGATE
    if confidence >= WATCH_THRESHOLD:
        return WATCH
    return INSUFFICIENT


def score_cluster(
    *,
    anomaly: float,
    independence: float,
    evidence: float,
    consistency: float,
    distinct_sources: int,
    contradiction_share: float,
    lab_negative: bool,
) -> dict:
    """Combine evidence factors (each in [0, 1]) into a confidence score and a tier.

    Caps are guard-rails: they can lower a tier but never raise it. A cluster can never be
    described as "confirmed" by this function.
    """
    factors = {
        "anomaly": anomaly,
        "independence": independence,
        "evidence": evidence,
        "consistency": consistency,
    }
    confidence = sum(WEIGHTS[name] * value for name, value in factors.items())
    tier = _tier_for(confidence)
    caps: list[str] = []

    def cap(limit: str, reason: str) -> None:
        nonlocal tier
        if _RANK[tier] > _RANK[limit]:
            tier = limit
            caps.append(reason)

    if lab_negative:
        cap(WATCH, "Laboratory result negative for the tested agent: capped at Watch")
    if distinct_sources < MIN_INDEPENDENT_SOURCES:
        cap(WATCH, f"Only {distinct_sources} independent source(s): capped at Watch")
    if contradiction_share >= CONTRADICTION_CAP_SHARE:
        cap(
            WATCH,
            f"{round(contradiction_share * 100)}% of reports contradict each other: capped at Watch",
        )

    return {
        "confidence": round(confidence, 3),
        "tier": tier,
        "factors": {name: round(value, 3) for name, value in factors.items()},
        "caps": caps,
    }
