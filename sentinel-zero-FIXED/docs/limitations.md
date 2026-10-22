# Limitations

SENTINEL ZERO is a prototype. Please read this before presenting or deploying it.

## What it does not do

- **It does not diagnose disease.** It flags spatial and temporal patterns for human review.
- **It does not confirm outbreaks or declare water unsafe.** Only laboratory testing and official
  investigation can do that.
- **It has not been validated on real data.** Every scenario in `app/synthetic.py` is invented. The
  tests show the logic behaves as designed on those scenarios, not how it would perform in the field.
- **It does not measure accuracy.** No detection lead time, false-alarm rate or missed-cluster rate has
  been measured. Those need real or consented historical data.

## Known weaknesses

| Area | Weakness | Mitigation in the prototype | Planned work |
|---|---|---|---|
| Contradiction detection | Keyword rule. "The water is not smelly now, but was yesterday" would be misread. | Caps tier at Watch; reports listed for review | Sentence-level NLP, with human-checked training data |
| Duplicate detection | Same-source similarity only. Paraphrased spam from many accounts is not caught. | Forwarded-text factor reduces independence | Cross-source near-duplicate detection |
| Clustering parameters | `eps` and `min_samples` set by hand | Documented in methodology | Tune on historical data with consent |
| Baseline | Built from the same dataset. Short histories give unstable baselines. | 0.5 floor; span floor of 1 day | Seasonal baselines from surveillance archives |
| Coordinates | Community reports are often vague about location | Locality names are used alongside coordinates | Geocoding quality checks; coarsened public maps |
| Language | Keyword rules are English-only | None | Odia and Hindi normalisation |
| Scale | O(n²) duplicate check | 5,000-report cap | Blocking by locality and time |

## Ethical and privacy considerations

- Community reports can identify people. A production system would coarsen locations and strip
  identifiers before display, and would keep only what it needs.
- A false alarm can harm a community's trust in its water supply or stigmatise an area. Output is
  framed as "Investigate" or "Watch" to prompt checking, never as a finding.
- Any real deployment would need data-sharing agreements with health and water authorities, and
  ethics review.

## Historical context

India's surveillance system (IDSP) relied on weekly paper-based reporting before moving toward
near-real-time reporting through IDSP-IHIP. Official responses to the June 2025 Jajpur outbreak
also disagreed on cause and magnitude. SENTINEL ZERO is designed to support the slow, verified
process, not to replace it.

## Added in v0.2

- **Replay has no background data.** Jajpur's baseline is almost empty, so the anomaly score is high for
  any cluster. Timing results are a mechanism demonstration only.
- **Hindi and Odia keyword lists are unreviewed.** Native-speaker checks are needed before any real reports
  are processed.
- **The water-network comparison is designed.** The hidden contamination and the network are chosen to show
  the mechanism. Results on one invented network are not evidence of superiority.
- **The baseline is deliberately naive.** Comparing against a stronger existing system (such as a standard
  surveillance threshold used by health departments) is still needed before any claim of improvement.
- **Greedy planning is not optimal.** The next-best-test planner is a greedy heuristic. It does not guarantee
  the best plan under the budget.

## Added in v0.3: live community feed

- **Posts are not moderated.** Anyone can post text. Spam, false reports and abuse are not filtered beyond exact-duplicate checks.
- **Storage is in memory.** The feed holds at most 500 posts and is cleared when the server restarts. It is not a record system.
- **Posts are placed at the locality centre.** Each post is given a random offset of about 0.5 km. Real posts would need a
  proper location method and privacy checks before any public display.
- **Source identifiers are pseudonymised in the feed**, but the server still sees the submitted identifier in memory.
- **The live feed is not an alert service.** A flag means a pattern to check. Nothing is sent to authorities.
- **Simulated posts are labelled as synthetic** in the demonstration controls. Do not mix them with real posts in any
  real deployment.
