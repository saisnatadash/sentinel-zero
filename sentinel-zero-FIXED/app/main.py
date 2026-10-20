"""FastAPI application: JSON API plus a single-page map dashboard."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .models import AnalysisRequest
from .pipeline import analyse
from .risk_engine import (
    CONTRADICTION_CAP_SHARE,
    INVESTIGATE_THRESHOLD,
    MIN_INDEPENDENT_SOURCES,
    WATCH_THRESHOLD,
    WEIGHTS,
)
from .synthetic import SCENARIOS, build_scenario

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "frontend" / "index.html"

app = FastAPI(
    title="SENTINEL ZERO",
    version="0.1.0",
    description="Prototype for flagging emerging patterns for human investigation. "
    "Uses synthetic demonstration data. It does not confirm outbreaks or certify water safety.",
)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(INDEX)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/api/methodology")
def methodology() -> dict:
    return {
        "weights": WEIGHTS,
        "thresholds": {"watch": WATCH_THRESHOLD, "investigate": INVESTIGATE_THRESHOLD},
        "caps": {
            "min_independent_sources": MIN_INDEPENDENT_SOURCES,
            "contradiction_share": CONTRADICTION_CAP_SHARE,
        },
        "note": "Rule-based and deliberately simple. Not calibrated against real outbreak data.",
    }


@app.get("/api/scenarios")
def list_scenarios() -> list[dict]:
    return [
        {"name": name, "label": s["label"], "description": s["description"], "expected": s["expected"]}
        for name, s in SCENARIOS.items()
    ]


@app.get("/api/scenarios/{name}")
def run_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{name}'")
    req = build_scenario(name)
    meta = SCENARIOS[name]
    return {
        "name": name,
        "label": meta["label"],
        "description": meta["description"],
        "expected": meta["expected"],
        "reports": [r.model_dump(mode="json") for r in req.reports],
        "labs": [lab.model_dump(mode="json") for lab in req.lab_results],
        "result": analyse(req),
    }


@app.post("/api/analyze")
def analyse_payload(req: AnalysisRequest) -> dict:
    return analyse(req)
