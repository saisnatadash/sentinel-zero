# Features (v0.2)

Every feature uses **synthetic data**. Each one answers a narrow question. None of them measures
real-world accuracy.

## 1. Invisible risk mapping

**Question:** where could water be unsafe, and do we actually have current evidence?

For each place in the network:

- `risk = max(hazard, exposure)`
  - `hazard = 0.2 + 0.4 (if supply interrupted) + min(0.3, 0.05 × recent reports) + 0.5 (if last test failed)`, capped at 1
  - `exposure = max(0.6 × hazard of each upstream interrupted stage)`
- `uncertainty = 1 − exp(−age_in_days ÷ 3)`; never tested = 1.0; failed test = 0.2

A place is an **invisible risk** when `risk ≥ 0.3` and `uncertainty ≥ 0.5`.

## 2. Failure-path reasoning

If a stage fails, every place downstream of it is affected. The output lists each one with its
number of stages away and the population it serves. The graph is a directed tree of
source → plant → tanks → distribution points.

## 3. Next-best-test planner

Greedy planning under a budget:

```
value(place) = risk × uncertainty × population_weight ÷ test_cost
population_weight = log(1 + population) ÷ log(1 + largest population)
```

After each pick, that place is treated as freshly tested, so it is not chosen twice. The planner
works on a copy of the network. It does **not** assume test results.

## 4. Jajpur 2025 timeline replay

Daily counts are scaled-down and shaped by reported milestones: first cases on 9 June, several hundred
affected by 10–11 June, cholera-positive samples reported on 14 June. On each day, the replay runs both
methods on the reports available up to that day and records when each first raises a flag.

**Limitation:** the Jajpur replay has no background data, so the baseline is almost empty. This means
the timing is a demonstration of the mechanism, not evidence that either method would have prevented harm.

## 5. Comparison with a simple rule

The simple rule raises an alert when a locality gets 5 or more relevant reports within 24 hours. It
has no de-duplication, no source check and no evidence check. On the five synthetic scenarios it raises
three false alarms (duplicates, contradictory reports, feast). The full system raises none.

## 6. "What would change this verdict"

Every cluster lists what would weaken or strengthen it: a negative lab result, a confirmed supply repair,
a single source or forwarded message, or a positive lab result. These items are also in the Markdown brief.

## 7. Hindi and Odia understanding

`app/lang.py` contains keyword lists for water odour, water colour and diarrhoea symptoms in English, Hindi and
Odia, and a negation check. Uncategorised reports are reclassified by keyword before clustering.
**These lists were drafted without native-speaker review and must be validated before real use.**

## 8. Exports

- `GET /api/scenarios/{name}/clusters.csv`: one row per cluster
- `GET /api/scenarios/{name}/brief.md`: investigation brief with disclaimer, alternative explanations,
  verdict checks and verification steps

## 9. Privacy by design

Cluster centroids are rounded to 2 decimal places (about 1 km). Reports are not stored by the service.
The analysis endpoint is stateless. A real deployment would also need access control and consent.

## 10. Five-view dashboard

Threat map, water network, Jajpur replay, method comparison and exports. The water network is drawn as an SVG
diagram. Each view runs without the map: if the Leaflet CDN is unavailable, the other four views still work.

## How the synthetic designs were chosen

The scenarios and the water network were designed to show each mechanism. For example, the water network hides
contamination at tank A and two distribution points, so the planning comparison favours the approach that uses
the network structure. That is a **designed demonstration**, not evidence that the approach beats other methods
on real systems. A real evaluation would need historical data and a prospective trial.
