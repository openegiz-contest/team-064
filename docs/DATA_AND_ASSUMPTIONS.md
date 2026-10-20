# Data and assumptions

## Public site facts

The twin uses Aktogay as a real-world reference for the site identity and
process route. KAZ Minerals describes Aktogay as an open-pit operation in
Kazakhstan with two sulphide concentrators and a combined design capacity of
50 Mt/year. Its public materials describe the original concentrator at 25
Mt/year and the second 25 Mt/year expansion.

Sources:

1. KAZ Minerals, [Annual Report and Accounts 2017](https://www.kazminerals.com/media/6188/kaz-minerals-2017-ara-web-ready-version.pdf),
   p. 30, Aktogay section. Reports 25 million tonnes per year capacity for the
   existing concentrator when fully ramped up and the expansion plan to double
   sulphide processing capacity to 50 million tonnes per year.
2. KAZ Minerals, [Aktogay](https://www.kazminerals.com/our-locations/aktogay/),
   official operations page, accessed 15 October 2026. Reports two sulphide
   concentrators with combined capacity of 50 Mtpa.
3. KAZ Minerals, [Aktogay expansion project approved](https://www.kazminerals.com/aktogay-expansion-project-approved/),
   2017. States that the first sulphide concentrator had 25 Mt/year capacity
   and the expansion would double it to 50 Mt/year.
4. KAZ Minerals, [Presidential opening of the Aktogay expansion project](https://www.kazminerals.com/presidential-opening-of-the-aktogay-expansion-project/),
   2021. Describes the new 25 Mtpa concentrator and the resulting 50 Mtpa
   combined sulphide capacity.

The model chooses one representative 25 Mt/year line. It does not represent
the site's two-line combined capacity as one line. The annualized simulator
basis is:

`3,200 t/h × 24 h/day × 365 day/year × 0.90 availability = 25.23 Mt/year`

The 3,200 t/h and 90% factor are synthetic model settings selected to express
one 25 Mt/year line. They are not statements of actual Aktogay operating
throughput or availability.

## Synthetic values and adjustable ranges

| Parameter | Default | UI range / rule |
|---|---:|---|
| Active 220 t trucks | 8 | 2–8; remaining twins are parked |
| Shovel loading | 6.5 min | 3–12 min, seeded ±8% variability; two shared resources |
| Main loaded haul | 9 min | 5–20 min; north leg duration ×1.45 |
| Empty return | 0.85 × loaded-leg duration | Longer alternative route remains effective |
| Main/north road distance | 3.8 / 5.2 km | Used only for average speed calculation; scene units are schematic |
| Ore-face grades F1/F2/F3 | 0.31 / 0.39 / 0.27 % Cu | Each 0.10–1.00 % Cu |
| Grade target | 0.34 % Cu | 0.15–0.80 % Cu; target may be infeasible for selected face grades |
| Base hardness | 12.4 kWh/t | 8–24; face offsets +0.6 / −0.9 / +2.6 |
| ROM capacity / initial inventory | 24,000 / 8,000 t | Initial grade 0.34%; hardness equals configured base |
| Crusher capacity | 3,200 t/h | 500–4,500 t/h |
| Specific combined plant energy | 21 kWh/t | Fixed illustrative intensity; 8 crusher + 13 concentrator |
| Available power | 75 MW | 10–90 MW; fault caps supply at min(configured,45) |
| Simulation speed | 60× | 1–180× |
| Seed | 64 | Integer 0–999999 |

One waste assignment occurs per eleven dispatches. SH-02 serves F2; SH-01 is a
shared loading resource for F1/F3/waste. Shovel relocation time is omitted.
The ROM dumping bay handles one truck at a time, with a 72-second service.
Grades and hardness are sampled at the start of loading and remain attached to
that material. New settings require pause and reset; speed alone changes live.
All of these are modeling assumptions, not disclosed Aktogay operating data.

## Accounting and response equations

- Ore residual: `initial_ROM + ore_mined − processed − current_ROM − ore_on_trucks`.
- Waste residual: `waste_mined − waste_dumped − waste_on_trucks`.
- Copper residual: `initial_ROM_Cu + mined_Cu − processed_Cu − ROM_Cu − truck_Cu`.
- All copper accounting uses **tonnes of contained copper**: `tonnes × grade_pct / 100`.
- ROM quality is mass-weighted. Processing removes ore, copper and hardness mass
  in the same proportion. Concentrate mass is `processed_Cu × recovery / 0.25`,
  assuming 25% Cu concentrate. That concentrate grade is synthetic too.
- Feed capacity is `min(crusher_tph × hardness_factor, available_MW × 1000 / 21)`.
- `hardness_factor = max(0.52, 1 − max(0, hardness−12) × 0.045)`.
- Actual processed tonnes are bounded by available ROM in each timestep. The
  displayed feed is the measured equivalent rate for the latest integration step.
- Recovery is bounded between 62% and 94% with a simple hardness penalty and
  grade adjustment; it is a teaching approximation, not a plant-performance curve.

The annual 90% operating factor above is used only for the design-capacity basis.
It is not applied again as a constant 10% derate at every processing step.

## Scenarios, prediction and geometry

Crusher downtime stops downstream feed because ROM is upstream. Existing
truck payloads are conserved during breakdown. Trucks committed to the main
road clear it; new trips use the north route, avoiding an instantaneous spatial
teleport. Low-grade and hard-ore changes apply to future samples; no fictitious
4 kt parcel is injected into ROM to force a response.

The paired experiment clones inventory, truck states and RNG, restores normal
conditions for one copy and applies the selected fault to the other, then
integrates both for 60 minutes. It is a conditional model experiment, not an
operating forecast calibrated to the real mine. Clearing a condition does not
remove material already mined under that condition.

3D coordinates are scene units, not surveyed metres. Truck and shovel size is
exaggerated for legibility. The renderer interpolates only between received
states; the backend controls all simulated progress. Road traffic spacing,
collisions, road gradients and shovel relocation are not modeled.

## Data rights

No mine datasets are redistributed. Public sources above are retained by link.
All operating inputs are original synthetic examples. Third-party graphics and
software are attributed in `ASSET_CREDITS.md`, under their original licenses.
