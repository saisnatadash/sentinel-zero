# Methodology

SENTINEL ZERO turns scattered community reports into a short list of clusters that need
human investigation. Every step is rule-based or uses a classical machine-learning method
(DBSCAN clustering). No step uses a large language model, and no step makes a final decision.

## Pipeline

```
Reports ──► 1. Clean and normalise text
        ──► 2. Remove duplicates           (same source, same place, <48 h, text similarity ≥ 0.90)
        ──► 3. Keep relevant categories    (water odour, water colour, diarrhoea symptoms)
        ──► 4. Spatio-temporal clustering  (DBSCAN; ≥4 reports per cluster)
        ──► 5. Anomaly vs baseline         (Poisson-style z-score against the locality's normal rate)
        ──► 6. Independence                (distinct sources; copied wording counts as half)
        ──► 7. Consistency                 (share of reports that contradict the water problem)
        ──► 8. Evidence                    (laboratory results within ±3 days, same locality)
        ──► 9. Score, cap and explain      (weighted confidence → tier; caps can only lower it)
```

## 1–2. Cleaning and duplicates

Text is lower-cased and stripped of punctuation. A report is treated as a duplicate when it comes
from the **same source**, in the **same locality**, within **48 hours**, and its wording is at least
90% similar (difflib `SequenceMatcher`). Duplicates are removed and listed, so reviewers can see
exactly what was dropped.

Only same-source repetition is removed automatically. Identical wording from *different* sources is
kept, but it is counted as forwarded text (see step 6).

## 3–4. Clustering

Relevant reports are projected onto a local plane:

- x = east–west distance in km, y = north–south distance in km
- t = hours since the first report × 0.25

DBSCAN runs with `eps = 2.5` and `min_samples = 4`. In practice this means four or more reports
that are roughly within 2.5 km and within about 10 hours of each other, chained together.
Parameters are set by hand for the synthetic scenarios and have not been tuned on real data.

## 5. Anomaly score

For each cluster, the expected count is:

```
expected = max( background_reports_in_locality_and_category / span_days × window_days , 0.5 )
z        = (n − expected) / √expected
anomaly  = clamp(z / 5, 0, 1)
```

`background_reports` excludes the cluster itself. The 0.5 floor stops a locality with no history
from producing an infinite score.

## 6. Independence

```
independence = clamp( (distinct_sources − 0.5 × forwarded) / n , 0, 1 )
```

A "forwarded" report repeats the exact normalised wording of an earlier report from another source.

## 7. Consistency

Water reports containing words such as *no*, *not*, *clear*, *normal*, *fine* or *without* are
treated as contradicting a water problem.

```
consistency = 1 − (contradictory reports / n)
```

This is a simple keyword rule. It will misread some sentences, which is listed in
[limitations.md](limitations.md).

## 8. Evidence

| Laboratory evidence in the same locality (±3 days) | Evidence factor |
|---|---|
| At least one positive result | 1.0 |
| Only negative results | 0.0 |
| None available | 0.3 (neutral; absence of evidence is not evidence of absence) |

## 9. Scoring and tiers

```
confidence = 0.35·anomaly + 0.25·independence + 0.25·evidence + 0.15·consistency
```

| Tier | Confidence |
|---|---|
| Investigate | ≥ 0.60 |
| Watch | 0.35 – 0.59 |
| Insufficient evidence | < 0.35 |

Caps can lower a tier, never raise it:

- A negative laboratory result caps the cluster at **Watch**.
- Fewer than **3** independent sources caps it at **Watch**.
- If **30% or more** of reports contradict each other, it is capped at **Watch**.

Every cluster carries its factors, any caps that applied, alternative explanations and suggested
verification steps. The system never labels a cluster "confirmed".

## What the synthetic scenarios show

These results come from `pytest` (see `tests/test_pipeline.py`). They show that the logic behaves as
designed on inputs built to test it. They are not measurements of real-world accuracy.

| Scenario | Reports | Duplicates removed | Clusters | Investigate | Watch | Why |
|---|---|---|---|---|---|---|
| Normal background | 40 | 0 | 0 | 0 | 0 | Not enough relevant reports to form a cluster |
| Genuine-style cluster | 54 | 0 | 1 | **1** | 0 | 14 sources, anomaly 1.0, positive lab |
| Copy-paste flood | 54 | 11 | 0 | 0 | 0 | After de-duplication, fewer than four reports remain |
| Contradictory reports | 50 | 0 | 1 | 0 | 1 | 45% of reports contradict each other → capped |
| Feast, negative lab | 48 | 0 | 1 | 0 | 1 | Negative lab → capped; "feast" listed as an alternative |
