# Evidence map

Criterion names and weights from the official Rules, edition 12 October 2026,
section 9: https://openegiz-contest.github.io/rules/ (rubric supplied by the participant).
This table describes evidence, not awarded levels or a predicted score.

| Criterion | Maximum | Implementation / evidence | Remaining verification |
|---|---:|---|---|
| Mine Model | 25 | 29 typed Ditto objects; containment, feeds, supply, road and loading relations in `setup_twins.py`; per-asset state in `app.telemetry()` | Confirm instantiated things on the real Stand |
| Mine Visualization | 25 | Interactive 3D pit, equipment, operation states, routes, stockpile and selection in `static/scene.js`; resource overlays and historical screenshots; v3 browser verification pending | Integrated browser run with platform source; judge-hardware performance |
| Behaviour Fidelity | 20 | Conserved ore, waste and copper; sampled loads; shovel/dump queues; finite ROM; power/hardness constraints; deterministic model tests | Site-specific calibration is out of scope; assumptions explicitly synthetic |
| Concept and Presentation | 15 | Team's original Aktogay dispatch/blending concept retained; source links and 25 Mt/year basis; updated `presentation.pdf` | Participant GitHub username still needs to be supplied by the team |
| What-if Scenarios | 10 | Eight code-free scenarios, propagation, restore/reset, visible active condition; local browser checks | Real MQTT/ Ditto scenario verification script |
| Modules | 5 | Adaptive dispatch changes assignments; processing/energy constraints change mine flow; paired forecast compares a real alternative from identical initial state | Confirm modules on the Stand with the supplied workflow |

Rules 6.2 and 9.3 require meaningful OpenEgiz operation. The integrated UI reads
its operator snapshot back from Ditto; standalone mode is clearly separate and
is not presented as satisfying that condition. Only the team-authored extensions
are described as submission contributions; the original Example Mine is not counted.
