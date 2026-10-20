# Submission: Aktogay Sulphide Shift Twin

Platform: OpenEgiz v1.0.4.

## Concept

**Enterprise:** The twin represents one sulphide ore value chain at the real
Aktogay open-pit copper operation in Kazakhstan: one representative pit phase,
haulage, a primary crusher, a ROM stockpile and one concentrator line.

**Users:** The primary user is the shift dispatcher, who assigns trucks to
faces and destinations. The shift mining engineer sets blend targets. The
plant shift supervisor needs an estimate of near-term feed rate, grade and
hardness.

**Decision:** After a crusher, truck, haul road or power disruption, how should
the dispatcher reassign trucks and adjust the ore blend to keep concentrator
feed as steady as the available fleet, stockpile and power allow?

**Why this choice:** The crusher and concentrator constrain the linked
production chain. A disruption changes truck cycles and queues, ROM inventory,
feed rate, feed quality, recovery and power demand. Dispatchers need to compare
these effects within a shift. The twin puts those connected states in a
spatial view and exposes repeatable what-if scenarios.

**Real or fictional:** Aktogay is the real site. KAZ Minerals reports the
original sulphide concentrator at 25 Mt/year in *Annual Report and Accounts
2017*, p. 30, and the later second 25 Mt/year concentrator, bringing the
sulphide design capacity to 50 Mt/year. This
submission models one representative 25 Mt/year line, not the whole mine or
plant. The simulation's capacity basis is 3,200 t/h × 24 h/day × 365 day/year
× 90% operating factor = 25.23 Mt/year, rounded to 25 Mt/year. The 90% factor
and 3,200 t/h operating value are modeling assumptions, not a published
Aktogay operating record. Public sources are listed in
`docs/DATA_AND_ASSUMPTIONS.md`.

## Team
|Tau-Ken Labs (Team-064); Majhabul Hoque Tahsim — sole member and developer|
| GitHub |
|---|
| @Catacombs666 |


## Mine

Version 2.0 represents 27 Eclipse Ditto things in namespace `org.aktogay`: the
mine, three areas, one pit phase, three ore faces, one waste cut, two haul roads,
two shared shovels, eight truck twins (2–8 active), a crusher, ROM stockpile,
concentrator, substation, maintenance crew and dispatch service. `_parents`
represents containment; `feeds`, `supplies`, `connects` and `loaded_by` record
process relationships. Three-dimensional scene positions are illustrative.

The mine is a seeded, bounded-step material-flow model. Shovel loading resources
and the ROM dump bay serialize service; vehicles carry sampled copper/hardness
through their full cycles. ROM capacity, crusher capacity, hardness and available
power constrain downstream flow. Ore, waste and contained-copper balances are
checked. The line design basis is not a guarantee of achieved shift production.

## Modules and What-if Scenarios

| Module | Working behavior | Where to inspect |
|---|---|---|
| Haulage and dispatch | Loading queues, loaded/empty travel, dump queue, fleet availability; adaptive face selection considers grade, hardness and shovel queue. Fixed rotation is a selectable comparison policy. | 3D trucks, asset inspector, dispatcher log, Settings |
| ROM, crushing and plant | Finite ROM, mass-weighted mixing, actual processed tonnes, hardness derate, power cap and synthetic recovery. | KPI strip, ROM pile, feed chart, crusher/plant/substation inspection |
| Paired decision experiment | Two 60-minute forecasts from the identical current material and random state: baseline versus chosen fault. Result passes through the platform. | Look one hour ahead; exportable confirmed report |

Start the run using **Start Simulation**. In **What-if laboratory**, choose a
card and press **Run selected scenario**. Changing the card alone changes no
operating state. All scenarios can be undone using **Restore normal conditions**;
**Reset** clears the shift counters and returns READY using the current settings.

| Scenario | Model consequence | What is visible |
|---|---|---|
| Crusher outage | Crusher throughput stops; arrivals fill ROM until trucks queue. ROM cannot feed past the stopped crusher. | Fault indication, zero feed, changing inventory, queue and event |
| Truck breakdown | HT-03 (or the first active truck in a two-truck fleet) stops in place; its payload remains accounted for. | Stationary failed asset, reduced active fleet, retained payload |
| Main road closure | Committed trucks clear the route; subsequent trips use the 45% longer-duration north route. | Closure barrier, changed truck routes, longer cycles |
| Power curtailment | Supply is capped at 45 MW or the configured lower supply. | Substation state; feed ≤ 45,000/21 = 2,143 t/h |
| Low-grade F2 | New loads sample 0.18% Cu. Existing loads retain their quality. | Face condition, dispatch choices and delayed mixed feed change |
| Hard F3 | New F3 loads sample 20 kWh/t. Adaptive dispatch can avoid F3. | Face condition, changed assignments; delayed or small plant response |

## Mine visualization

**http://localhost:8091** provides a locally bundled Three.js scene: graded pit
benches and ramp, moving articulated haul trucks, shared excavators, crusher,
ROM, conveyors, concentrator and substation. Orbit/pan/zoom, Fit/Top view and asset
inspection support exploration. Trucks follow confirmed route progress; loading,
dumping, breakdown, road closure and plant status are reflected visually.

The UI does not combine initial twin values with newer local events. The entire
operator snapshot is published through MQTT and read back from one Ditto feature,
with a run ID, sequence and timestamp. Stale state holds the scene and is labelled.
The separate local development mode is explicitly labelled and is not the Stand.

## Data and Assumptions

The published Aktogay identity, process route and line capacity remain the only
real-site grounding. Every operating grade, cycle, fleet setting, inventory,
recovery response and coordinate is synthetic. See `docs/DATA_AND_ASSUMPTIONS.md`
for sources, equations and ranges; `ASSET_CREDITS.md` for third-party graphics rights.
Settings apply to a new paused/ready shift, so changes do not erase in-flight
material during normal operation. The model is not calibrated to operator records.

## What works and what does not

Implemented and exercised locally: model/API tests, full baseline haul cycles,
all six scenario controls, pause/resume/reset, validated settings, 3D WebGL,
asset inspection, paired forecast, responsive interface and report export.
Browser evidence in `docs/evidence/` is explicitly local-mode evidence.

**Not yet verified:** Docker/Stand startup, real broker delivery and Ditto
acceptance, Telegraf/InfluxDB ingestion and Grafana display. Docker is absent in
the authoring environment. Run `bash scripts/verify-aktogay.sh` after the integrated
startup; it checks these paths and writes an honest pass/fail report. A broker
publish alone is never treated as confirmation of a twin update.

## Limitations

The model has shared shovel resources, but no shovel relocation time, detailed
truck collision/overtaking dynamics, surveyed terrain, road gradient model,
calibrated comminution circuit, fuel consumption, automatic repair duration,
tailings management or operational safety logic. Road lengths and 3D scene units
are different scales; equipment is enlarged for readability. Graphics quality
is selectable and software rendering has a reduced-resolution profile. All
state is in memory and a service restart begins a new shift; reports can be exported.

## Presentation

`presentation.pdf` describes the concept, 3D controls, platform data path,
scenario behavior, paired experiment, data assumptions and verification boundary.
