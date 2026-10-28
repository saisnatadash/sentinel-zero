# SENTINEL ZERO

**AI-powered early detection of emerging community threats.** Team Sentinel, HSC|OR|00084, Odisha.

SENTINEL ZERO connects scattered community reports about water and health, checks whether a pattern is credible, and passes the evidence to people for investigation. It flags patterns for human review. It does not diagnose disease, confirm outbreaks or certify water safety.

> **Prototype.** Scenarios, the water network and the demonstration posts are synthetic. The live feed is not moderated and is held in memory. See [limitations](sentinel-zero-FIXED/docs/limitations.md).

## Where to look

| What | Where |
|---|---|
| Full project README, API and features | [sentinel-zero-FIXED/README.md](sentinel-zero-FIXED/README.md) |
| Application code (pipeline, scoring, water network, API) | [sentinel-zero-FIXED/app](sentinel-zero-FIXED/app) |
| Dashboard (single page: live feed, charts, map) | [sentinel-zero-FIXED/frontend/index.html](sentinel-zero-FIXED/frontend/index.html) |
| Method: how scores and caps are built | [docs/methodology.md](sentinel-zero-FIXED/docs/methodology.md) |
| Architecture | [docs/architecture.md](sentinel-zero-FIXED/docs/architecture.md) |
| Features and what each one shows | [docs/features.md](sentinel-zero-FIXED/docs/features.md) |
| Limitations and ethics | [docs/limitations.md](sentinel-zero-FIXED/docs/limitations.md) |
| Hosting on Render | [demo/DEPLOY.md](sentinel-zero-FIXED/demo/DEPLOY.md) |
| Tests | [sentinel-zero-FIXED/tests](sentinel-zero-FIXED/tests) |

## Run it locally

Requires Python 3.11 or later.

```bash
cd sentinel-zero-FIXED
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000. Example posts are loaded at start-up; set `SEED_DEMO=0` to start with an empty live feed.

Run the tests:

```bash
cd sentinel-zero-FIXED
python -m pytest -q
```

## Technology

Python, FastAPI, scikit-learn (DBSCAN), NumPy, Leaflet with OpenStreetMap, Docker.

## Data and references

Public figures are cited in the dashboard's references slide and in [sentinel-zero-FIXED/README.md](sentinel-zero-FIXED/README.md). All scenario data is synthetic.

## Licence

MIT. See [sentinel-zero-FIXED/LICENSE](sentinel-zero-FIXED/LICENSE).
