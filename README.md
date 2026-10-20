# Aktogay · Shift Operations 2.0

An interactive 3D digital twin of one representative Aktogay sulphide line:
pit faces → haulage → ROM → primary crusher → concentrator feed.
Operating inputs and terrain are synthetic. Site identity and the approximately
25 Mt/year line basis are grounded in the sources in
[Data and Assumptions](docs/DATA_AND_ASSUMPTIONS.md).

## Start the OpenEgiz submission

Requirements: Docker Engine/Desktop running, Docker Compose v2.20+, Python 3,
`make`, and at least 6 GiB available to Docker. First startup downloads platform
images and one pinned Python dependency. No account, API key or paid service is
needed. All browser graphics dependencies and textures are bundled locally.

On Ubuntu, install the missing command-line prerequisite:

```bash
sudo apt-get update
sudo apt-get install -y make
```

From the repository root (the directory containing this README and Makefile):

```bash
make aktogay
```

Open **http://localhost:8091**, then click **Start Simulation**. Startup leaves
the model READY so the beginning of the shift is visible. When running, trucks
complete loading, haul, dump and return cycles, the simulated clock advances,
and the KPI/chart values update. The header must show **DITTO CONFIRMED** for an
integrated run. It does not label missing or stale state as live.

Grafana: **http://localhost:3000** → Dashboards → OpenEgiz Examples →
**Aktogay Sulphide Shift Twin**. Login is `admin` with the generated
`GRAFANA_ADMIN_PASSWORD` in `deploy/compose/.env`. Keep that file private.

### Updating an existing local installation

Copy the updated source files into your existing project folder, preserving
`deploy/compose/.env` and Docker volumes. Then run `make aktogay` again; it
rebuilds the image with the new model and locally bundled 3D files. Reload the
browser with Ctrl+Shift+R. No `make clean` is required.

On the team's Windows/WSL installation:

```bash
cd /mnt/e/team-064-main
make aktogay
```

Run these commands in Ubuntu, with Ubuntu enabled in Docker Desktop → Settings
→ Resources → WSL Integration. A Windows drive E: appears as `/mnt/e/` in WSL.

## Operator workflow

1. **Start Simulation**. The default clock is 60×, or one simulated minute per
   real second. Choose 1×, 10×, 30×, 60×, 120× or 180× using Time scale.
2. Drag the scene to orbit; right-drag to pan; scroll to zoom. Fit view and Top
   restore useful camera positions. Click equipment or an asset label to inspect
   its current state. Geometry is schematic and equipment is enlarged for clarity.
3. Open **What-if laboratory**, select a disruption, and click **Run selected
   scenario** while running. Merely selecting a card does not change the mine.
   The active condition appears beneath the controls and in the dispatcher log.
4. **Restore normal conditions** clears the fault without discarding material
   already mined or processed. **Reset** creates a new READY shift with the
   current settings and an 8,000 t ROM; it does not delete Docker data.
5. **Pause Simulation**, then open **Settings**. Apply & reset shift validates
   inputs and starts a new READY shift. Settings cannot silently alter an ongoing
   material inventory. Time scale alone can be changed while running.
6. **Compare next 60 min** performs two seeded forecasts from the same current
   inventory/RNG state: normal conditions versus the selected disruption. It
   does not advance the operating run. This result also returns through Ditto.
7. **Export run** downloads the confirmed snapshot, assumptions/settings,
   recent history, event log and paired forecast as JSON.

The ROM is upstream of the crusher. It stores incoming ore during a crusher
outage; it cannot bypass the stopped crusher to keep the plant fed. Grade and
hardness changes affect newly sampled loads, then travel through haulage and
ROM blending. Consequently not every scenario causes an instantaneous feed
change. The hard-F3 scenario may have little feed effect when adaptive dispatch
avoids that face; the changed face twin and later assignments remain visible.

## Verify

Model and HTTP API tests (standard Python library only):

```bash
make test-aktogay
```

After the real Docker stack is running, verify MQTT → Ditto, confirmed state,
all scenarios, balances, pause/reset, InfluxDB and Grafana:

```bash
bash scripts/verify-aktogay.sh
```

This exercises and resets the in-memory simulation. It writes
`docs/evidence/stand-report.json`; a failing check returns a nonzero exit code.
Optional browser test instructions are in [Validation](docs/VALIDATION_REPORT.md).

**Verification boundary:** the bundled model/API and browser reports were
produced with the same simulation/service in explicitly labelled local mode.
Docker is unavailable in the authoring environment. Integrated startup, Ditto
acceptance, Grafana ingestion and clean-machine startup duration still require
the above Stand check. They are not claimed as passed.

## Lightweight local preview (not an OpenEgiz Stand)

To inspect the 3D interface and exercise the same model without Docker:

```bash
make aktogay-local
```

Open http://localhost:8091. The header states **LOCAL MODEL · PLATFORM OFF**.
This mode does not connect to MQTT, Ditto or Grafana and is not the contest
execution path. Do not run it on the same port as the integrated service.

## Stop, status and troubleshooting

```bash
make ps
make logs S=aktogay-mine
make down
```

`make down` preserves platform volumes; restarting the simulator creates a new
in-memory shift. Export a report before stopping if it is needed. `make clean`
deletes platform volumes and credentials and is not needed for this update.

| Symptom | Action |
|---|---|
| Start disabled / WAITING FOR DITTO | Inspect `make logs S=aktogay-mine` and `make logs S=ditto-connectivity`; the overlay requires a confirmed `operator_state` feature, not just an MQTT connection. |
| Old 2D interface | Rebuild with `make aktogay`, then hard-refresh the browser. |
| SIM clock/events/KPIs disagree | Version 2 uses one atomic platform snapshot. Verify the image was rebuilt and that the new API returns `snapshot` and `transport`. |
| Slow graphics | Use the efficient/default quality and a smaller window. Software renderers are detected automatically. High quality increases pixel density and requires more rendering capacity. |
| 3D unavailable | Enable browser hardware acceleration/WebGL. A graphics error is reported; no static image is passed off as 3D. |
| Docker unavailable in Ubuntu | Enable Ubuntu WSL integration and check that `docker version` lists both Client and Server. |

## Important files

- `team/aktogay/model.py`: seeded queues, haul cycles, balances, blending and energy limits.
- `team/aktogay/app.py`: controls, MQTT protocol, atomic Ditto readback and HTTP/static server.
- `team/aktogay/static/scene.js`: original procedural 3D scene and state-driven equipment.
- `team/aktogay/static/ui.js`, `style.css`: controls, charts, settings and inspection.
- `team/aktogay/setup_twins.py`: 27 twins, containment and process relations.
- `docs/EVIDENCE_MAP.md`: official criterion-to-implementation mapping.
- `ASSET_CREDITS.md`: bundled graphics sources, licenses and checksums.
- `presentation.pdf`: current project presentation and verification boundary.

Own contributions: MIT. OpenEgiz and third-party components retain their licenses.
