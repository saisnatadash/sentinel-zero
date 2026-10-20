# SENTINEL ZERO

### AI-powered early detection of emerging community threats

SENTINEL ZERO connects scattered community reports, tests whether a cluster is credible, and passes
the evidence to people for investigation. It works on water-quality and symptom reports, starting
with Odisha.

> **Prototype status.** This code runs on **synthetic demonstration data only**. It flags patterns
> for human review. It does not diagnose disease, confirm outbreaks or certify water safety.

## Why it matters

- Only 76% of India's population used safely managed drinking water in 2024 (UN SDG data).
- The June 2025 diarrhoea outbreak in Jajpur, Odisha, spread across several localities within days.
  Official reports and local explanations initially disagreed on the cause.
- Warning signs are often present in fragmented reports before they are visible in official data.

## What it does

| Step | What happens |
|---|---|
| Duplicate removal | Repeated posts from one source are removed and listed. |
| Clustering | Reports close in space and time are grouped (DBSCAN). |
| Anomaly check | Each cluster is compared with its locality's normal background rate. |
| Independence | Distinct sources count; copied wording counts as half. |
| Consistency | Reports that contradict the water problem lower confidence. |
| Evidence | Laboratory results in the same locality adjust the score. |
| Output | Investigate, Watch or Insufficient evidence, with factors, caps, alternative explanations and suggested checks. |

Full details: [docs/methodology.md](docs/methodology.md).

## Quick start

Requires Python 3.11 or later.

```bash
git clone https://github.com/YOUR-USERNAME/sentinel-zero.git
cd sentinel-zero
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000> and choose a scenario.

### Run the tests

```bash
python -m pytest -q
```

Expected: `8 passed`.

### Regenerate the sample data

```bash
python -m app.synthetic
```

This writes `data/sample_reports.csv` and `data/sample_labs.csv`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/scenarios` | List synthetic scenarios |
| GET | `/api/scenarios/{name}` | Run one scenario (reports, labs and result) |
| POST | `/api/analyze` | Analyse your own JSON payload (see `app/models.py`) |
| GET | `/api/methodology` | Weights, thresholds and caps |

Interactive API documentation is available at `/docs`.

Example request body for `/api/analyze`:

```json
{
  "reports": [
    {
      "id": "R1", "text": "water smells bad near our tap",
      "lat": 20.85, "lon": 86.33, "timestamp": "2026-09-01T10:00:00",
      "locality": "Jajpur", "source_id": "user-17", "category": "water_odour"
    }
  ],
  "lab_results": []
}
```

## Deploy a live link

The app is packaged with a `Dockerfile`, so it runs on any host that supports Docker. Two free
options are described in [demo/DEPLOY.md](demo/DEPLOY.md):

- **Render** (web service from this GitHub repository)
- **Hugging Face Spaces** (Docker SDK)

## Project structure

```
app/            FastAPI app, pipeline, risk engine, synthetic scenarios
frontend/       Single-page dashboard (Leaflet + OpenStreetMap)
tests/          Behavioural tests on synthetic scenarios
data/           Exported synthetic data (CSV)
docs/           Architecture, methodology, limitations
demo/           Video script and deployment guide
```

## Technology

Python · FastAPI · scikit-learn (DBSCAN) · NumPy · Leaflet · OpenStreetMap · Docker

## Limitations

Read [docs/limitations.md](docs/limitations.md) before using or presenting this project. In short:
it has not been validated on real data, its contradiction detection is keyword-based, and its
thresholds are hand-set.

## Data sources and references

- UN SDG 6 India snapshot (2024): <https://www.sdg6data.org/country-or-area/India>
- WHO/UNICEF JMP 2025 global data, via Our World in Data: <https://ourworldindata.org/grapher/proportion-using-safely-managed-drinking-water>
- Jajpur outbreak reporting (PTI via The Week; UNI; OdishaBytes), June 2025
- IDSP-IHIP transition, NCDC newsletter: <https://ncdc.mohfw.gov.in/wp-content/uploads/2024/07/Volume-12-Issue-4-Oct-23-to-Dec-23.pdf>
- Jal Jeevan Mission Odisha functionality assessment: <https://jaljeevanmission.gov.in>

## Licence

MIT. See [LICENSE](LICENSE).
