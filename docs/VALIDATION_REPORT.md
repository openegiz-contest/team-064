# Version 3 validation

31 Python model/API tests pass. See `evidence/unit-tests.txt`.
Coverage includes finite depletion, road headway, gradient and bucket effects,
shovel faults, matched experiments, reset, telemetry definitions and conservation.

`evidence/dispatch-benchmark.json` records 25 paired experiments (50 model runs),
five seeds and five conditions over four simulated hours. It includes model SHA256,
all runs and aggregate differences. Run `make benchmark-aktogay` to reproduce.

JavaScript syntax checks pass. Browser rendering was not verified: the installed
Playwright package had no Chromium executable and its download failed; the remote
browser could not open the local preview. Historical v2 screenshots/report are
under `evidence/historical-v2/` and are not v3 test results.

Docker is unavailable here. Full startup, MQTT delivery, Ditto readback, InfluxDB,
Grafana and clean-machine reproducibility remain unverified. The user's supplied
screenshots show their earlier working system, not an independent v3 test.

Before submission run `make aktogay`, `make test-aktogay` and
`bash scripts/verify-aktogay.sh`. Check all eight scenarios in the 3D interface,
resource overlay, pause and dispatch experiment, including the low-grade tradeoff.
Run `node scripts/verify_aktogay_browser.cjs` with Playwright/Chromium installed
for automated browser checks. No commit or push was made in this environment.
