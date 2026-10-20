# Demo guide (3–5 minute video)

The competition requires a 3–5 minute video at 720p or higher, under 80 MB, in MP4 or MOV format.

## Before recording

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Open `http://localhost:8000`. Confirm that all five scenario buttons load and that the banner says
the data is synthetic.

## Script

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:25 | Dashboard banner and header | "SENTINEL ZERO flags emerging community threats for human investigation. It is a prototype, and it works only on synthetic data." |
| 0:25–0:55 | Scenario 1 (normal) | "Most reports are unrelated. Nothing is flagged, which is the correct result." |
| 0:55–1:55 | Scenario 2 (genuine-style cluster) | "Fourteen people report water or symptom problems in one town within a day, and a lab result is positive. It is flagged for investigation. Look at the factors and the suggested verification steps." |
| 1:55–2:35 | Scenario 3 (copy-paste flood) | "One account posted the same message twelve times. The system removes the eleven duplicates. No cluster forms." |
| 2:35–3:15 | Scenario 4 (contradictory) | "Half the reports say the water smells and half say it is clear. Confidence is capped at Watch because the reports contradict each other." |
| 3:15–3:50 | Scenario 5 (feast) | "Eight people report stomach upset after a feast, and the lab result is negative. Watch, with the feast listed as an alternative explanation." |
| 3:50–4:20 | Terminal: `pytest -q` | "Eight automated tests check these behaviours. They are tests on synthetic inputs, not evidence of accuracy in the field." |
| 4:20–end | README limitations section | "The next step is a pilot with real, consented data and a health or water partner." |

## Tips

- Keep the banner visible in every shot.
- Do not claim accuracy, lead time or real detections.
- Record at 1280×720 or higher. Keep the file under 80 MB.
