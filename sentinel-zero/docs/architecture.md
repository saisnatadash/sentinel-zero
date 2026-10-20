# Architecture

## Components

```
┌──────────────────────────────┐        HTTP/JSON         ┌────────────────────────────────┐
│ Browser: frontend/index.html │ ───────────────────────► │ FastAPI  (app/main.py)         │
│ Leaflet map, cluster panel   │ ◄─────────────────────── │  /api/scenarios  /api/analyze  │
└──────────────────────────────┘                          │  /api/methodology  /api/health │
                                                          └───────────────┬────────────────┘
                                                                          │
                                                          ┌───────────────▼────────────────┐
                                                          │ Pipeline (app/pipeline.py)     │
                                                          │  dedupe → cluster → score      │
                                                          └───────┬───────────────┬────────┘
                                                                  │               │
                                              ┌───────────────────▼──┐   ┌────────▼─────────────┐
                                              │ Risk engine          │   │ Synthetic scenarios  │
                                              │ (app/risk_engine.py) │   │ (app/synthetic.py)   │
                                              │ weights, tiers, caps │   │ deterministic, seeded│
                                              └──────────────────────┘   └──────────────────────┘
```

## Design decisions

- **Stateless analysis.** Each request contains its own reports. Nothing is stored, which keeps the
  prototype simple and limits privacy exposure. A production version would add a database (PostgreSQL
  with PostGIS) and access control, as described in the roadmap.
- **Pure functions.** `analyse()` takes data and returns data. Tests call it directly, with no
  server or database needed.
- **Explainable scoring.** Each tier comes from named factors and named caps, not from an opaque model.
- **Synthetic-first.** The app ships only with labelled synthetic scenarios. Real data requires
  data-sharing agreements and ethics review, which are outside this prototype's scope.

## Request flow

1. The browser calls `GET /api/scenarios/{name}`.
2. The server builds the scenario (seeded), runs `analyse()` and returns the reports, lab results and
   result together.
3. The browser draws reports as grey dots, labs as markers and clusters as circles coloured by tier,
   then fills the side panel from the same response.

## Complexity

Duplicate detection compares each report with earlier kept reports, which is O(n²) in the worst case.
This is acceptable for the 5,000-report limit in `AnalysisRequest`. A production system would use
blocking by locality and time to bring this down.

## Roadmap (not implemented)

- CSV upload with schema validation
- PostgreSQL/PostGIS storage and an audit trail of decisions
- Multilingual text normalisation (Odia and Hindi)
- Calibration of thresholds against historical, consented data
