"""Tests for the v0.2 features. All data is SYNTHETIC. Results show designed behaviour, not field accuracy."""
from fastapi.testclient import TestClient

from app import water_network as wn
from app.baseline import baseline_alerts
from app.lang import classify, has_negation
from app.main import app
from app.pipeline import analyse, normalise
from app.replay import run_replay
from app.synthetic import build_scenario

client = TestClient(app)


# --- multilingual rules -----------------------------------------------------------------

def test_hindi_and_odia_reports_are_classified():
    assert classify("पानी से बदबू आ रही है") == "water_odour"
    assert classify("ଦୁର୍ଗନ୍ଧ ଆସୁଛି") == "water_odour"
    assert classify("दस्त हो रहे हैं") == "diarrhoea_symptoms"
    assert classify("bus fare increased") == "other"


def test_hindi_and_odia_negation_is_detected():
    assert has_negation("पानी साफ है")
    assert has_negation("water is clear today")
    assert not has_negation("water smells bad")


def test_normalise_keeps_non_latin_letters():
    assert "पानी" in normalise("पानी!!")


def test_pipeline_reclassifies_uncategorised_reports():
    from app.models import AnalysisRequest, Report
    from datetime import datetime, timedelta
    t0 = datetime(2026, 9, 1, 6)
    reports = [Report(id=f"H{i}", text="पानी से बदबू", lat=20.85, lon=86.33,
                      timestamp=t0 + timedelta(hours=i), locality="Jajpur",
                      source_id=f"s{i}", category="other") for i in range(6)]
    result = analyse(AnalysisRequest(reports=reports))
    assert result["summary"]["relevant_reports"] == 6
    assert result["clusters"], "reclassified Hindi reports should form a cluster"


# --- verdict checks and privacy ---------------------------------------------------------

def test_every_cluster_lists_what_would_change_the_verdict():
    for name in ("true_cluster", "contradictory", "coincidental"):
        for c in analyse(build_scenario(name))["clusters"]:
            assert len(c["what_would_change_verdict"]) >= 3


def test_cluster_centroids_are_rounded_for_privacy():
    for c in analyse(build_scenario("true_cluster"))["clusters"]:
        assert len(str(c["centroid"]["lat"]).split(".")[-1]) <= 2


# --- baseline comparison ----------------------------------------------------------------

def test_simple_rule_raises_false_alarms_that_the_full_system_avoids():
    rows = {r["scenario"]: r for r in client.get("/api/compare").json()["rows"]}
    assert rows["true_cluster"]["sentinel_caught"] and rows["true_cluster"]["baseline_caught"]
    for name in ("duplicates", "contradictory", "coincidental"):
        assert rows[name]["baseline_false_alarm"]
        assert not rows[name]["sentinel_false_alarm"]
    totals = client.get("/api/compare").json()["totals"]
    assert totals["sentinel_false_alarms"] == 0
    assert totals["baseline_false_alarms"] >= 3


def test_baseline_has_no_alert_on_normal_background():
    assert baseline_alerts(build_scenario("normal")) == []


# --- Jajpur replay ----------------------------------------------------------------------

def test_replay_is_labelled_synthetic_and_timing_is_reported():
    replay = run_replay()
    assert "synthetic" in replay["label"].lower()
    assert "not case data" in replay["disclaimer"].lower()
    assert replay["first_sentinel_investigate"] is not None
    assert replay["first_baseline_alert"] is not None
    assert replay["first_sentinel_investigate"] <= replay["first_baseline_alert"]


def test_replay_endpoint_returns_daily_series():
    body = client.get("/api/replay").json()
    assert len(body["days"]) == 6
    counts = [d["reports_to_date"] for d in body["days"]]
    assert counts == sorted(counts)


# --- water network ----------------------------------------------------------------------

def test_failure_path_shows_downstream_places():
    net = wn.build_network()
    names = [p["id"] for p in wn.failure_path(net, "tank_A")]
    assert names == ["dist_1", "dist_2"]


def test_disrupted_tank_is_an_invisible_risk():
    net = wn.build_network()
    ids = [r["id"] for r in wn.invisible_risks(net)]
    assert "tank_A" in ids


def test_next_best_tests_respect_budget_and_do_not_repeat():
    net = wn.build_network()
    picks = wn.next_best_tests(net, budget=3)
    ids = [p["id"] for p in picks]
    assert len(ids) == len(set(ids))
    assert sum(p["cost"] for p in picks) <= 3


def test_sentinel_planning_beats_oldest_first_and_random_on_designed_network():
    net = wn.build_network()
    values = [c["contaminated_places_found"] for c in wn.compare_strategies(net, budget=3)]
    assert values[0] >= values[1] >= 0
    assert values[0] >= values[2]


def test_water_endpoint_respects_budget_parameter():
    body = client.get("/api/water?budget=2").json()
    assert body["budget"] == 2
    assert len(body["next_tests"]) <= 2
    assert client.get("/api/water?budget=99").status_code == 422


# --- exports ----------------------------------------------------------------------------

def test_csv_export_has_header_and_rows():
    r = client.get("/api/scenarios/true_cluster/clusters.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0].startswith("cluster_id,locality,tier")
    assert "Investigate" in r.text


def test_markdown_brief_carries_disclaimer_and_verdict_checks():
    r = client.get("/api/scenarios/true_cluster/brief.md")
    assert r.status_code == 200
    assert "does not certify water safety" in r.text
    assert "What would change this verdict" in r.text


def test_exports_reject_unknown_scenarios():
    assert client.get("/api/scenarios/nope/brief.md").status_code == 404
    assert client.get("/api/scenarios/nope/clusters.csv").status_code == 404


def test_logo_and_dashboard_are_served():
    assert client.get("/logo.png").status_code == 200
    assert client.get("/").status_code == 200
