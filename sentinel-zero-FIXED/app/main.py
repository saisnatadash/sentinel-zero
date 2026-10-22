"""FastAPI application: JSON API, exports and a single-page dashboard."""
import csv
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response

from . import water_network as wn
from .baseline import baseline_alerts
from .models import AnalysisRequest
from .pipeline import DISCLAIMER, analyse
from .replay import run_replay
from .risk_engine import CONTRADICTION_CAP_SHARE, INVESTIGATE_THRESHOLD, MIN_INDEPENDENT_SOURCES, WATCH_THRESHOLD, WEIGHTS
from .synthetic import SCENARIOS, build_scenario

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
