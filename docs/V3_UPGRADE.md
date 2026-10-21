# Aktogay v3 upgrade and demonstration

Tau-Ken Labs (Team-064). Sole member and developer: Majhabul Hoque Tahsim.

## Installation into your existing GitHub working folder

1. Back up your current working folder. Extract this ZIP into a separate folder.
2. Copy the contents of `team-064-v3` into your existing repository folder,
   replacing matching files. Preserve your `.git`, `deploy/compose/.env` and Docker
   volumes. This archive contains no `.env` credentials. Do not delete volumes.
3. Restore your GitHub username in SUBMISSION.md if you filled it previously.
4. In Ubuntu/WSL, change into the existing repository and run:

```bash
make aktogay
make test-aktogay
bash scripts/verify-aktogay.sh
```

5. Open http://localhost:8091 and press Ctrl+Shift+R. Confirm DITTO CONFIRMED,
   then follow the demonstration below. A standalone preview is not submission
   evidence of OpenEgiz integration.
6. Review the changes in GitHub Desktop. Commit and push only after the Stand
   verifier passes and you have checked the interface. The new source is not
   already on GitHub. Keep your participant metadata and organizer files intact.

## What changed

| Area | Version 3 contribution | How to verify |
|---|---|---|
| Mine Model | 29 twins including waste/tailings accounts; live reserves, roads and shovels | Inspect assets and Ditto telemetry |
| Behaviour | Reserve depletion, headway queues, grade/distance travel, bucket passes, partial-load preservation | Tests and resource constraints |
| Visualization | Resource overlay, shrinking reserve markers, road state/queue labels, fault/queue markers | Toggle Overlay, run congestion and outage |
| Scenarios | Shovel outage and road congestion join the existing six | Select and apply each scenario |
| Modules | Explainable adaptive selection and matched policy experiments | Pause, run comparison, inspect grade/production/ROM |
| Evidence | Five-seed benchmark, balance residuals, explicit limitations | Benchmark JSON and validation report |

## Five-minute demonstration

1. Start baseline. Enable Overlay: resources. Inspect a face, road and shovel.
2. Run road congestion. Observe admission queues and increasing waiting time.
3. Restore, then run shovel outage. SH-02 stops and existing partial payload
   remains accounted for. Observe available-face assignments and later feed effects.
4. Pause. Run a 240-minute dispatch experiment under baseline. Compare production,
   grade error, energy and final ROM. The current shift does not advance.
5. Run a low-grade experiment. Explain the infeasible target warning and the
   production/grade tradeoff. Restore conditions before continuing.
6. Export the confirmed report. Show the five material balance residuals.

For a quick depletion demo: pause, open Settings, set each face reserve to 225 t,
apply/reset, start at 180x. Faces eventually deplete; restore does not replenish.
Reset restores the configured reserve for a new shift.

## Submission boundary

All operating parameters and geometry are synthetic. Aktogay identity and line
capacity have public sources. Grade/road models are illustrative, not calibrated.
The benchmark supports conditional model comparisons, not real production gains.
V3 passes model/API tests, but browser and Docker integration remain to be checked
on the user's installation. No maximum score or competition result is guaranteed.
