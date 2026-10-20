# Validation report

## Results for the 3D revision

- 21 Python unit/API tests pass. Exact output: `docs/evidence/unit-tests.txt`.
  Coverage includes an eight-hour baseline, all six scenarios, ore/waste/copper
  conservation, seeded comparisons, parameter limits, HTTP controls, pause/reset,
  stale readback and the Ditto topic regression.
- 17 local browser checks pass with no console or JavaScript errors. See
  `docs/evidence/browser-report.json` for the recorded time and exact checks.
  The test exercises actual HTTP-backed model state, WebGL rendering, clock and
  truck movement, all six scenario buttons, settings, completed haul cycles,
  paired forecasting, asset selection and mobile overflow.
- The recorded software-rendered browser measured approximately 18 FPS in the
  efficient mode. This is a short sample, not a sustained benchmark or a promise
  of game-level frame rates. High-quality mode increases rendering cost.
- Screenshots in `docs/evidence/` show the local standalone mode explicitly.
  They do not demonstrate a successful MQTT/Ditto deployment.
- The revised six-page presentation was rendered and visually reviewed.

## Defects addressed

The publisher used REST-style colon-separated thing IDs in Ditto protocol topics.
Protocol topics now use namespace/name, while REST IDs retain namespace:name.
Previously the operator screen could mix stale platform KPIs with advancing local
log entries. Integrated mode now displays one atomic, sequenced operator snapshot
read back from Ditto; commands have visible acknowledgement and freshness status.
There is no silent local fallback. Missing and stale data are not labelled live.

The model also corrects a percent-to-fraction error in accumulated concentrate,
preserves grades of already loaded material, increases subsequent haul duration
for a closed road, and changes future hard-ore loads instead of creating an
unaccounted stockpile parcel. Loading and dumping resources have finite queues.
These fixes are covered by tests; actual broker acceptance still needs the Stand.

## Not verified here

Docker is unavailable in this workspace. Full Compose startup, actual MQTT delivery,
Ditto readback, InfluxDB ingestion, Grafana operation and clean-room startup time
remain unverified. The extracted project has no .git directory, so git status and
`git fetch origin` cannot establish divergence or organizer updates. No commit or
push was made. The participant GitHub username remains for the team to supply.

## Reproduce

```sh
make test-aktogay
# Optional local browser check; install Playwright and its Chromium first:
npm install --prefix /tmp/aktogay-browser playwright@1.51.1
/tmp/aktogay-browser/node_modules/.bin/playwright install chromium
PLAYWRIGHT_MODULE=/tmp/aktogay-browser/node_modules/playwright node scripts/verify_aktogay_browser.cjs --standalone
# Docker Desktop with Ubuntu WSL integration enabled:
make aktogay
bash scripts/verify-aktogay.sh
```

The integrated verifier checks fresh platform readback, controls, six scenarios,
material balance, a paired forecast, recent InfluxDB feed data and Grafana health
and dashboard provisioning. It writes `docs/evidence/stand-report.json`. Run it on
an evaluation/demo shift: it deliberately resets and changes simulation state.
Review the operator view at http://localhost:8091 as well. Rubric implications and
remaining evidence are mapped in `docs/EVIDENCE_MAP.md`.
