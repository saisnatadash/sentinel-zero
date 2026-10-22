"""FastAPI application: JSON API, exports and a single-page dashboard."""
import csv
import hashlib
import io
import os
import random
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from . import water_network as wn
from .baseline import baseline_alerts
from .lang import classify
from .models import AnalysisRequest, Report
from .pipeline import DISCLAIMER, analyse
from .replay import run_replay
from .risk_engine import CONTRADICTION_CAP_SHARE, INVESTIGATE_THRESHOLD, MIN_INDEPENDENT_SOURCES, WATCH_THRESHOLD, WEIGHTS
from .synthetic import LOCALITIES, SCENARIOS, build_scenario

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "frontend" / "index.html"
LOGO = ROOT / "frontend" / "logo.png"

app = FastAPI(
    title="SENTINEL ZERO",
    version="0.2.0",
    description="Prototype for flagging emerging patterns for human investigation. "
    "Uses synthetic demonstration data. It does not confirm outbreaks or certify water safety.",
)


def _scenario_or_404(name: str) -> None:
    if name not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{name}'")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(INDEX)


@app.get("/logo.png", include_in_schema=False)
def logo() -> FileResponse:
    return FileResponse(LOGO)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/api/methodology")
def methodology() -> dict:
    return {
        "weights": WEIGHTS,
        "thresholds": {"watch": WATCH_THRESHOLD, "investigate": INVESTIGATE_THRESHOLD},
        "caps": {"min_independent_sources": MIN_INDEPENDENT_SOURCES,
                 "contradiction_share": CONTRADICTION_CAP_SHARE},
        "languages": ["English", "Hindi", "Odia"],
        "note": "Rule-based and deliberately simple. Not calibrated against real outbreak data.",
    }


@app.get("/api/scenarios")
def list_scenarios() -> list[dict]:
    return [{"name": name, "label": s["label"], "description": s["description"], "expected": s["expected"]}
            for name, s in SCENARIOS.items()]


@app.get("/api/scenarios/{name}")
def run_scenario(name: str) -> dict:
    _scenario_or_404(name)
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


@app.get("/api/scenarios/{name}/clusters.csv")
def export_clusters_csv(name: str) -> Response:
    _scenario_or_404(name)
    result = analyse(build_scenario(name))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["cluster_id", "locality", "tier", "confidence", "reports", "distinct_sources",
                     "window_hours", "explanation", "verification_steps"])
    for c in result["clusters"]:
        writer.writerow([c["cluster_id"], c["locality"], c["tier"], c["confidence"], c["report_count"],
                         c["distinct_sources"], c["window_hours"], c["explanation"],
                         " | ".join(c["verification_steps"])])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}_clusters.csv"'})


@app.get("/api/scenarios/{name}/brief.md")
def export_brief(name: str) -> Response:
    _scenario_or_404(name)
    result = analyse(build_scenario(name))
    s = result["summary"]
    lines = [
        f"# SENTINEL ZERO investigation brief: {SCENARIOS[name]['label']}",
        "",
        f"> {DISCLAIMER}",
        "> Synthetic demonstration data only.",
        "",
        f"Reports: {s['total_reports']} · Duplicates removed: {s['duplicates_removed']} · "
        f"Investigate: {s['investigate_count']} · Watch: {s['watch_count']}",
        "",
    ]
    if not result["clusters"]:
        lines.append("No cluster met the minimum size. Nothing is flagged.")
    for c in result["clusters"]:
        lines += [
            f"## {c['cluster_id']} · {c['locality']} · {c['tier']} ({round(c['confidence'] * 100)}%)",
            "",
            c["explanation"],
            "",
            "**Alternative explanations**",
            *[f"- {a}" for a in c["alternative_explanations"]],
            "",
            "**What would change this verdict**",
            *[f"- {a}" for a in c["what_would_change_verdict"]],
            "",
            "**Suggested verification**",
            *[f"- {a}" for a in c["verification_steps"]],
            "",
        ]
    return Response("\n".join(lines), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="{name}_brief.md"'})


@app.get("/api/replay")
def replay() -> dict:
    return run_replay()


@app.get("/api/compare")
def compare() -> dict:
    rows = []
    for name in SCENARIOS:
        req = build_scenario(name)
        result = analyse(req)
        base = baseline_alerts(req)
        is_real = name == "true_cluster"
        inv = result["summary"]["investigate_count"]
        rows.append({
            "scenario": name,
            "label": SCENARIOS[name]["label"],
            "real_cluster": is_real,
            "sentinel_investigate": inv,
            "sentinel_watch": result["summary"]["watch_count"],
            "baseline_alerts": len(base),
            "sentinel_false_alarm": (not is_real) and inv > 0,
            "baseline_false_alarm": (not is_real) and len(base) > 0,
            "sentinel_caught": is_real and inv > 0,
            "baseline_caught": is_real and len(base) > 0,
        })
    totals = {
        "sentinel_false_alarms": sum(r["sentinel_false_alarm"] for r in rows),
        "baseline_false_alarms": sum(r["baseline_false_alarm"] for r in rows),
        "sentinel_caught": sum(r["sentinel_caught"] for r in rows),
        "baseline_caught": sum(r["baseline_caught"] for r in rows),
    }
    return {"rows": rows, "totals": totals,
            "note": "Five synthetic scenarios, one of which is a real-style cluster. Small sample; "
                    "shows behaviour on designed cases, not accuracy in the field."}


@app.get("/api/water")
def water(budget: float = Query(3, ge=1, le=6)) -> dict:
    net = wn.build_network()
    nodes = [{
        "id": nid, "kind": n.kind, "name": n.name, "population": n.population, "x": n.x, "y": n.y,
        "last_test_days": n.last_test_days, "last_result": n.last_result, "disrupted": n.disrupted,
        "recent_reports": n.recent_reports, "risk": wn.risk(net, nid), "uncertainty": wn.uncertainty(n),
        "reasons": wn.reasons(net, nid), "failure_path": wn.failure_path(net, nid),
    } for nid, n in net.nodes.items()]
    return {
        "nodes": nodes,
        "edges": [{"from": u, "to": v} for u, v in net.edges],
        "invisible_risks": wn.invisible_risks(net),
        "next_tests": wn.next_best_tests(net, budget),
        "comparison": wn.compare_strategies(net, budget),
        "budget": budget,
        "disclaimer": "Synthetic network. Places are invented. Contamination is hidden and used only to score strategies.",
    }


@app.get("/api/methodology/water")
def water_method() -> dict:
    return {"tau_days": wn.TAU_DAYS,
            "note": "Uncertainty = 1 − exp(−age ÷ τ); never tested = 1.0. Hazard combines disruption, "
                    "recent reports and failed tests. Exposure passes 60% of an upstream disrupted stage's hazard downstream."}


@app.post("/api/analyze")
def analyse_payload(req: AnalysisRequest) -> dict:
    return analyse(req)


# ---------- live community feed (in memory, resets when the server restarts) ----------

LIVE_LIMIT = 500          # oldest posts are dropped beyond this
SIMULATE_MAX = 20         # one request may add at most this many simulated posts
_live: list[Report] = []
_live_lock = threading.Lock()


class LivePost(BaseModel):
    text: str = Field(min_length=3, max_length=280)
    locality: str
    source_id: str = Field(default="citizen", min_length=1, max_length=40)


def _pseudonym(source_id: str) -> str:
    """Public feeds show a short hash of the source, never the raw identifier."""
    return "src-" + hashlib.sha1(source_id.encode()).hexdigest()[:6]


def _store(text: str, locality: str, source_id: str, when: datetime | None = None) -> Report:
    lat, lon = LOCALITIES[locality]
    # Jitter of about 0.5 km so posts from one place do not sit on a single point.
    # Coordinates are also coarsened in outputs, so this stays approximate.
    report = Report(
        id="L-" + uuid.uuid4().hex[:8], text=text,
        lat=round(lat + random.uniform(-0.005, 0.005), 4),
        lon=round(lon + random.uniform(-0.005, 0.005), 4),
        timestamp=(when or datetime.now()).replace(microsecond=0),
        locality=locality, source_id=source_id, category=classify(text),
    )
    with _live_lock:
        _live.append(report)
        del _live[:-LIVE_LIMIT]
    return report


@app.get("/api/localities")
def localities() -> list[str]:
    return list(LOCALITIES)


@app.post("/api/live/report", status_code=201)
def live_report(post: LivePost) -> dict:
    if post.locality not in LOCALITIES:
        raise HTTPException(status_code=400, detail=f"Unknown locality '{post.locality}'")
    r = _store(post.text.strip(), post.locality, post.source_id)
    return {"accepted": True, "id": r.id, "category": r.category, "locality": r.locality}


@app.post("/api/live/simulate")
def live_simulate(locality: str = Query("Jajpur"), n: int = Query(6, ge=1, le=SIMULATE_MAX)) -> dict:
    """Adds clearly labelled SYNTHETIC posts from distinct sources. For demonstrations only."""
    if locality not in LOCALITIES:
        raise HTTPException(status_code=400, detail=f"Unknown locality '{locality}'")
    texts = ["water smells bad near our tap", "tap water has a strange smell",
             "several people in our lane have loose motions", "brown water coming from the pipe"]
    for i in range(n):
        _store(random.choice(texts), locality, f"sim-{uuid.uuid4().hex[:6]}")
    return {"added": n, "locality": locality, "note": "Synthetic posts for demonstration."}


@app.delete("/api/live")
def live_clear() -> dict:
    with _live_lock:
        _live.clear()
    return {"cleared": True}


@app.get("/api/live")
def live_feed() -> dict:
    with _live_lock:
        snapshot = list(_live)
    req = AnalysisRequest(reports=snapshot, lab_results=[])
    public = [{**r.model_dump(mode="json"), "source_id": _pseudonym(r.source_id)} for r in snapshot]
    return {
        "name": "live",
        "label": "Live community reports",
        "description": "Posts from the public form. Each post is classified, de-duplicated, clustered and scored.",
        "expected": "Clusters appear once several distinct sources report close together in space and time.",
        "reports": public,
        "labs": [],
        "result": analyse(req),
        "total_posts": len(snapshot),
    }


# Example posts so the live feed is not empty on first load. Set SEED_DEMO=0 to start empty.
# They are synthetic, written for demonstration, and come from pseudonymous demo sources.
EXAMPLE_POSTS = [
    ("Jajpur", "water smells bad near our tap", 50),
    ("Jajpur", "tap water has a strange smell since morning", 42),
    ("Jajpur", "several people in our lane have loose motions", 37),
    ("Jajpur", "brown water coming from the pipe", 31),
    ("Jajpur", "water smells like sewage at the tank", 24),
    ("Jajpur", "stomach upset after drinking tap water", 18),
    ("Cuttack", "power cut for two hours yesterday", 40),
    ("Puri", "bus fare increased again", 33),
    ("Balasore", "school timings changed this week", 22),
    ("Berhampur", "water looks yellowish from the tap", 12),
]


def seed_example_posts() -> None:
    if os.environ.get("SEED_DEMO", "1") != "1":
        return
    now = datetime.now()
    for i, (locality, text, minutes_ago) in enumerate(EXAMPLE_POSTS):
        _store(text, locality, f"demo-{i:02d}", when=now - timedelta(minutes=minutes_ago))


seed_example_posts()
