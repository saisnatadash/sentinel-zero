"""Behavioural tests on SYNTHETIC scenarios. These show the pipeline handles the cases it was
designed for. They do not measure real-world accuracy (see docs/limitations.md)."""
from fastapi.testclient import TestClient

from app.main import app
from app.models import AnalysisRequest
from app.pipeline import analyse
from app.synthetic import build_scenario


def run(name: str) -> dict:
    return analyse(build_scenario(name))


def test_normal_background_produces_no_investigation():
    assert run("normal")["summary"]["investigate_count"] == 0


def test_genuine_style_cluster_is_flagged_with_positive_lab_evidence():
    result = run("true_cluster")
    assert result["summary"]["investigate_count"] >= 1
    top = result["clusters"][0]
    assert top["tier"] == "Investigate"
    assert top["locality"] == "Jajpur"
    assert top["distinct_sources"] >= 3
    assert top["factors"]["evidence"] == 1.0


def test_copy_paste_flood_is_deduplicated_and_forms_no_cluster():
    result = run("duplicates")
    assert result["summary"]["duplicates_removed"] == 11
    assert result["summary"]["clusters"] == 0
    assert result["summary"]["investigate_count"] == 0


def test_contradictory_reports_cap_the_tier_at_watch():
    result = run("contradictory")
    assert result["summary"]["investigate_count"] == 0
    top = result["clusters"][0]
    assert top["tier"] == "Watch"
    assert any("contradict" in cap.lower() for cap in top["caps"])


def test_negative_lab_result_prevents_investigation_and_explains_alternatives():
    result = run("coincidental")
    assert result["summary"]["investigate_count"] == 0
    top = result["clusters"][0]
    assert top["tier"] == "Watch"
    alternatives = " ".join(top["alternative_explanations"]).lower()
    assert "feast" in alternatives
    assert "negative" in alternatives


def test_analysis_is_deterministic():
    assert run("true_cluster") == run("true_cluster")


def test_empty_input_returns_no_clusters():
    result = analyse(AnalysisRequest(reports=[]))
    assert result["summary"]["clusters"] == 0
    assert result["summary"]["total_reports"] == 0


def test_api_endpoints():
    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"
    names = {s["name"] for s in client.get("/api/scenarios").json()}
    assert names == {"normal", "true_cluster", "duplicates", "contradictory", "coincidental"}
    body = client.get("/api/scenarios/true_cluster").json()
    assert body["result"]["summary"]["investigate_count"] >= 1
    assert len(body["reports"]) > 0
    assert client.get("/api/scenarios/does-not-exist").status_code == 404
    assert client.get("/api/methodology").status_code == 200
    assert client.get("/").status_code == 200
