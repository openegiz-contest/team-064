# Twin graph and state contract

`setup_twins.py` creates 27 things under `org.aktogay`. All use the platform's
`default:basic_policy`. The original mine concept and scope are retained.

| Things | Type / hierarchy | Main states |
|---|---|---|
| mine-01 | Mine root | Simulation clock/status/run ID, feed, grade, recovery, mass residual, atomic operator snapshot |
| area-pit / area-plant / area-utilities | Areas under mine | Structural grouping |
| phase-sulphide-01 | Pit phase under pit area | Schematic scene location |
| face-west / face-east / face-north | Ore faces under phase | Grade, hardness, material; loaded_by shovel relation |
| face-waste | Waste cut under phase | Waste material |
| road-main / road-north | Roads under pit area | Open/closed, occupancy, connects pit to ROM |
| shovel-01 / shovel-02 | Shared loading resources | Loading/available, loading rate |
| truck-01 … truck-08 | Haul fleet under phase | Cycle state, payload, sampled material, face, route, route progress, speed, trips, assignment reason |
| rom-01 | Stockpile under plant | Tonnes, fill percentage, mixed grade/hardness; feeds crusher |
| crusher-01 | Crusher under plant | Running/fault, throughput, processed tonnes, crusher power; feeds concentrator |
| concentrator-01 | Concentrator under plant | Feed, grade, recovery, concentrate rate and plant power |
| substation-01 | Power supply under utilities | Supply limit and demand; supplies crusher/concentrator |
| maintenance-crew-01 | Crew under utilities | Available/working and broken truck ID |
| dispatcher-01 | Decision service under mine | Active scenario, policy, grade target, route, last decision and count |

`attributes._parents` records containment; process relationships use explicit
`feeds`, `supplies`, `connects` and `loaded_by` attributes. Asset `scene_position`
values are schematic, not geographic coordinates. Vehicles use their assigned
route plus `route_position` for moving placement.

## Protocol

REST thing identifier: `org.aktogay:truck-01`.
Ditto protocol topic: `org.aktogay/truck-01/things/twin/commands/modify`.
The namespace/name separator in the protocol is a slash. The prior colon was
invalid and allowed local model events to progress without twin updates.
MQTT transport topic remains `telemetry/truck-01`. Every publication replaces
`/features`, using `{feature: {properties: {value, unit?}}}` so platform
Telegraf field names remain `value_<feature>_properties_value`.

The mine's `operator_state` feature is a JSON string containing the complete
snapshot. All UI operating values and history come from this one confirmed
feature, eliminating mixed clocks/events/KPIs. It includes its own run ID,
sequence and publication timestamp. Numeric features continue independently
for Grafana. See `ARCHITECTURE.md` for readback and freshness behavior.
