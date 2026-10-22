"""Behaviour of the live community feed (in-memory). Uses synthetic posts only."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_function():
    client.delete("/api/live")


def test_simulated_posts_form_a_flagged_cluster():
    client.post("/api/live/simulate?locality=Jajpur&n=8")
    data = client.get("/api/live").json()
    assert data["total_posts"] == 8
    assert data["result"]["summary"]["clusters"] == 1
    assert data["result"]["clusters"][0]["locality"] == "Jajpur"


def test_posts_are_classified_and_sources_pseudonymised():
    r = client.post("/api/live/report", json={"text": "water smells bad near our tap",
                                               "locality": "Puri", "source_id": "my-phone"})
    assert r.status_code == 201
    assert r.json()["category"] == "water_odour"
    feed = client.get("/api/live").json()["reports"]
    assert feed[-1]["source_id"].startswith("src-")
    assert "my-phone" not in str(feed)


def test_unknown_locality_is_rejected():
    r = client.post("/api/live/report", json={"text": "water smells bad", "locality": "Nowhere"})
    assert r.status_code == 400


def test_too_short_text_is_rejected():
    r = client.post("/api/live/report", json={"text": "hi", "locality": "Puri"})
    assert r.status_code == 422


def test_clear_empties_the_feed():
    client.post("/api/live/simulate?locality=Cuttack&n=3")
    client.delete("/api/live")
    assert client.get("/api/live").json()["total_posts"] == 0
