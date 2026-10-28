# Architecture

SENTINEL ZERO is a single FastAPI service with a single-page dashboard. It has no database. The live
community feed is held in memory and is cleared when the server restarts.

## Components

```
Browser: frontend/index.html (one page, plain JavaScript, Leaflet)
   |  live tab, dashboard, threat map, water network, replay, compare, export
   |  HTTP / JSON
   v
FastAPI: app/main.py
   |-- /api/live*        live feed: store posts (in memory), analyse them
   |-- /api/scenarios*   synthetic scenarios, CSV and Markdown exports
   |-- /api/analyze      analyse any JSON payload (reports and lab results)
   |-- /api/water        water network: risk, invisible risks, next tests, strategies
   |-- /api/replay       Jajpur timeline replay (synthetic counts)
   |-- /api/compare      Sentinel Zero versus a simple rule, across the scenarios
   |-- /api/methodology  weights, thresholds and caps
   |
   +--> app/pipeline.py      classify -> dedupe -> cluster -> score -> explain
   |      +--> app/lang.py          keyword rules (English, Hindi, Odia), negation check
   |      +--> app/risk_engine.py   weights, tiers, caps
   |      +--> app/models.py        request and record types (pydantic)
   |
   +--> app/baseline.py      simple rule: 5 relevant reports in 24 hours
   +--> app/replay.py        Jajpur timeline replay
   +--> app/water_network.py simulated network: risk, uncertainty, failure path, planner
   +--> app/synthetic.py     deterministic synthetic scenarios (seeded)
```

## Analysis pipeline (`app/pipeline.py`)

1. **Classify.** Reports without a category are classified by keywords in English, Hindi or Odia.
2. **De-duplicate.** A report is a duplicate when it has the same source, the same locality, a
   timestamp within 48 hours and text similarity of at least 0.9.
3. **Keep relevant reports.** Only water-smell, water-colour and diarrhoea-symptom reports are clustered.
4. **Cluster.** DBSCAN (scikit-learn) on coordinates in kilometres plus time (0.25 km per hour).
   Parameters: `eps = 2.5`, `min_samples = 4`.
5. **Score.** Each cluster gets anomaly (against the locality's background rate), independence
   (distinct sources, with forwarded copies counted as half), evidence (laboratory results in the same
   locality), and consistency (share of reports that deny a water problem). See
   `docs/methodology.md` for the weights.
6. **Cap and explain.** Caps stop a cluster reaching a higher tier without enough independent sources or
   evidence. Each cluster lists its alternative explanations, what would change the verdict, and the
   checks to run.

## Live feed (`app/main.py`)

- `POST /api/live/report` stores one post. The server classifies the text, sets the locality centre
  with about 0.5 km of random offset, and gives the post an identifier.
- `GET /api/live` runs the pipeline on the stored posts. Source identifiers are shown as short hashes.
- The store holds at most 500 posts. Older posts are dropped first. A lock guards it.
- `SEED_DEMO=1` (the default) loads example posts at start-up. `SEED_DEMO=0` starts empty.

## Frontend (`frontend/index.html`)

- **Live reports:** posting form, demonstration controls, live flags and feed. Refreshes every 10 s.
- **Dashboard:** charts over time, by tier, by locality and against the thresholds. Data source can be
  the live feed or a scenario.
- **Threat map:** clusters as shaded areas (convex hull of member reports, coloured by tier, shaded by
  confidence). Reports are dots coloured by type.
- **Water network, replay, compare, export:** as described in the README.

No external JavaScript or CSS is needed except Leaflet and OpenStreetMap tiles.

## Design decisions

- **Explainable scoring.** Every tier comes from named factors and named caps, not an opaque model.
  No generative AI makes a flag.
- **Pure analysis functions.** `analyse()` takes data and returns data. Tests call it directly.
- **Privacy by design.** Outputs round coordinates to about 1 km. Public feeds show pseudonymous
  source identifiers. Synthetic data is labelled in the interface.
- **Prototype storage.** The live feed is in memory on purpose. A production version would use
  PostgreSQL with PostGIS, access control and an audit trail.

## Complexity

Duplicate detection compares each report with earlier kept reports, which is O(n²) in the worst case.
The analysis endpoint caps input at 5,000 reports and the live feed at 500 posts. A production version
would use blocking by locality and time.

## Testing

`tests/` holds three test modules, run with `python -m pytest -q` from `sentinel-zero-FIXED/`:

- `test_pipeline.py`: the core pipeline, scoring and caps on the synthetic scenarios.
- `test_features.py`: the ten features (invisible risks, failure paths, planner, replay, comparison,
  Hindi and Odia handling, exports, privacy rounding).
- `test_live.py`: the live feed (classification, pseudonyms, validation, clearing).

## Roadmap (not implemented)

- CSV upload with schema validation
- PostgreSQL/PostGIS storage and an audit trail of decisions
- Moderation of public posts and rate limits per source
- Native-speaker review of the Hindi and Odia keyword lists
- Calibration of thresholds against historical, consented data
- Comparison with an established surveillance threshold used by health departments
