# Architecture · version 2

## Integrated execution

`make aktogay` runs the OpenEgiz Compose stack, initialises 29 Ditto twins, then
starts the Python model/API/static service. The simulation starts READY.

Control button → local HTTP command → validated model transition → MQTT
`telemetry/<entity>` → Ditto protocol `org.aktogay/<entity>/things/twin/commands/modify`
→ Ditto twin → authenticated REST readback → `/api/state` → 3D UI and charts.

Numeric per-asset features retain the `/features` replacement shape expected by
Telegraf. The platform also emits them to InfluxDB and the existing Grafana dashboard.

## Consistent state

The mine twin includes `operator_state`, a JSON-encoded string containing the
complete UI snapshot: vehicles, process metrics, clock, events, history, settings,
run ID, sequence and optional paired forecast. Each snapshot is one atomic feature
replacement. The UI never combines its values with a newer local-model snapshot.
The HTTP state endpoint returns only the confirmed snapshot plus separately labelled
transport diagnostics. The aggregate snapshot is published after the asset features.

A single publishing lock preserves command/heartbeat order. A readback worker checks
Ditto every ~0.7 seconds without blocking UI requests on 29 serial REST calls. Snapshot
age, not successful MQTT enqueueing, determines freshness (under 6 seconds). A stale
snapshot holds the scene; an absent snapshot shows a waiting panel instead of zeros.
The same snapshot is republished while paused so a paused model can remain connected.

## Simulator

`model.py` is deterministic for the seed, settings and action schedule. Seconds are
integrated in substeps no larger than five seconds. Two shared shovel resources,
one ROM dump bay, vehicle loads, finite ROM and constrained processing are coupled.
The HTTP thread and simulation loop share a reentrant state lock. Speed can change
while running; other settings require pause and reset to a new inventory baseline.

`compare()` deep-copies the current model and RNG for paired forecasts. It preserves
the operating model; its results are returned via the same Ditto snapshot.

## Graphics

`scene.js` uses vendored Three.js r180, OrbitControls and geometry merge utilities.
Ground comes from a locally bundled CC0 ambientCG texture. All equipment and terrain
meshes are original procedural geometry. Static meshes and fixed equipment parts are
batched; shadows for static structures are computed once, and vehicles use simple
contact shadows. Software renderers use a reduced pixel ratio. Camera interaction and
state interpolation run locally, but no frontend timer independently advances the mine.
Interpolation is bounded between received positions; it cannot invent new trips.

## API

| Method/path | Purpose |
|---|---|
| GET `/api/state` | `{snapshot, transport, server_time}`; snapshot is null until confirmation |
| GET `/api/scenarios` | Scenario catalogue and default settings |
| GET `/healthz` | 200 only while the configured source is fresh; includes explicit source/mode |
| POST `/api/control` | `{"action":"start"}`, `pause`, `resume`, or `{"action":"speed","speed":60}` |
| POST `/api/scenario` | `{"id":"power-limit"}` or `baseline`; run must be active |
| POST `/api/reset` | New READY shift preserving validated settings |
| POST `/api/settings` | Partial validated settings; paused/ready only; resets model |
| POST `/api/compare` | `{"id":"power-limit"}`; computes a paired 60-minute forecast |

A successful command means accepted, not yet confirmed by Ditto. The UI tracks the
accepted sequence and indicates confirmation pending. Invalid JSON, invalid settings,
unknown controls and invalid operation states return an explicit HTTP 400.

## Local preview boundary

`AKTOGAY_MODE=standalone` uses the same model and service with a direct local snapshot.
The banner explicitly says LOCAL MODEL / PLATFORM OFF. This developer-only route
supports tests when Docker is unavailable; it is not the contest deployment and
is never used automatically as a fallback in integrated mode.

V3 adds POST `/api/experiment` with scenario `id` and integer `minutes` (30–480).
Pause first. The service compares rotation/adaptive clones and returns the result
through the same confirmed snapshot. Reset clears previous results.
