#!/usr/bin/env python3
"""Create the Aktogay sulphide-line twin hierarchy in Eclipse Ditto."""
import base64
import json
import os
import time
import urllib.error
import urllib.request

NS = "org.aktogay"
POLICY = "default:basic_policy"


def feature(value, unit=None):
    p = {"value": value}
    if unit:
        p["unit"] = unit
    return {"properties": p}


def thing(name, label, kind, parent=None, attrs=None, features=None):
    a = {"name": label, "kind": kind, "_isType": False}
    if parent:
        a["_parents"] = f"{NS}:{parent}"
    if attrs:
        a.update(attrs)
    return {"policyId": POLICY, "attributes": a, "features": features or {}}


def twins():
    result = {
        "mine-01": thing("mine-01", "Aktogay sulphide value chain", "mine", attrs={"operator": "KAZ Minerals", "region": "Abay, Kazakhstan"}, features={
            "ore_mined": feature(0, "t"), "waste_mined": feature(0, "t"),
            "crusher_feed_rate": feature(0, "t/h"), "feed_grade": feature(0, "% Cu"),
            "feed_hardness": feature(0, "kWh/t"), "copper_recovery": feature(0, "%"),
            "concentrate_rate": feature(0, "t/h"), "scenario": feature("baseline"),
            "mass_balance_error": feature(0, "t"), "simulation_time": feature(0, "min")}),
        "area-pit": thing("area-pit", "Sulphide pit phase", "area", "mine-01", {"coordinates": {"x": 12, "y": 49}}),
        "area-plant": thing("area-plant", "Crushing and concentration", "area", "mine-01", {"coordinates": {"x": 86, "y": 51}}),
        "area-utilities": thing("area-utilities", "Power and maintenance", "area", "mine-01", {"coordinates": {"x": 76, "y": 83}}),
        "phase-sulphide-01": thing("phase-sulphide-01", "Representative sulphide phase", "pit-phase", "area-pit", {"coordinates": {"x": 22, "y": 42}}),
    }
    face_data = [
        ("face-west", "West ore face F1", 0.31, 13.0, 18, 26),
        ("face-east", "East ore face F2", 0.39, 11.5, 31, 20),
        ("face-north", "North ore face F3", 0.27, 15.0, 39, 39),
    ]
    for name, label, grade, hardness, x, y in face_data:
        result[name] = thing(name, label, "ore-face", "phase-sulphide-01", {
            "coordinates": {"x": x, "y": y}, "baseline_grade_pct": grade,
            "baseline_hardness_kwh_t": hardness}, {
            "grade": feature(grade, "% Cu"), "hardness": feature(hardness, "kWh/t"),
            "available_tonnes": feature(85000, "t"), "material": feature("ore")})
    result["face-waste"] = thing("face-waste", "Waste cut W1", "waste-face", "phase-sulphide-01", {
        "coordinates": {"x": 18, "y": 31}}, {"grade": feature(0, "% Cu"), "material": feature("waste")})
    roads = [
        ("road-main", "Main haul road", 16, 36, 78, 43, 3.8),
        ("road-north", "North alternate haul road", 34, 24, 72, 44, 5.2),
    ]
    for name, label, x1, y1, x2, y2, length in roads:
        result[name] = thing(name, label, "haul-road", "area-pit", {
            "coordinates": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}, "length_km": length,
            "capacity_trucks_per_hour": 36}, {"state": feature("open"), "closed": feature(False), "occupancy": feature(0, "trucks")})
    for idx, (face, x, y) in enumerate([("face-west", 25, 39), ("face-east", 32, 23)], 1):
        name = f"shovel-{idx:02d}"
        result[name] = thing(name, f"Hydraulic shovel SH-{idx:02d}", "shovel", "phase-sulphide-01", {
            "coordinates": {"x": x, "y": y}, "rated_tph": 4200, "bucket_t": 45,
            "assigned_face": f"{NS}:{face}"}, {"state": feature("available"), "payload_rate": feature(0, "t/h"), "availability": feature(0.94, "ratio")})
    for idx in range(1, 9):
        name = f"truck-{idx:02d}"
        result[name] = thing(name, f"Haul truck HT-{idx:02d}", "haul-truck", "phase-sulphide-01", {
            "capacity_t": 220, "coordinates": {"x": 22 + idx * 2, "y": 44}}, {
            "state": feature("queue_at_shovel"), "payload": feature(0, "t"),
            "material": feature("ore"), "assigned_face": feature("face-west"),
            "destination": feature("crusher"), "speed": feature(0, "km/h"),
            "route_position": feature(0, "ratio"), "fuel": feature(100, "%"),
            "trips_total": feature(0, "trips"), "dispatch_reason": feature("baseline cycle")})
    result["crusher-01"] = thing("crusher-01", "Primary gyratory crusher CR-01", "crusher", "area-plant", {
        "coordinates": {"x": 75, "y": 42}, "rated_tph": 3200, "power_kwh_per_t": 8}, {
        "state": feature("running"), "throughput": feature(0, "t/h"),
        "feed_grade": feature(0, "% Cu"), "feed_hardness": feature(0, "kWh/t"),
        "rom_level": feature(0, "t"), "tonnes_total": feature(0, "t"),
        "power_draw": feature(0, "MW"), "availability": feature(0.90, "ratio")})
    result["rom-01"] = thing("rom-01", "Run-of-mine stockpile", "stockpile", "area-plant", {
        "coordinates": {"x": 80, "y": 29}, "capacity_t": 24000}, {
        "level": feature(8000, "t"), "fill_pct": feature(33.3, "%"),
        "grade": feature(0.34, "% Cu"), "hardness": feature(12.4, "kWh/t")})
    result["concentrator-01"] = thing("concentrator-01", "Sulphide concentrator line 01", "concentrator", "area-plant", {
        "coordinates": {"x": 89, "y": 46}, "design_tph": 3200,
        "design_mtpa": 25, "energy_kwh_per_t": 13}, {
        "state": feature("running"), "feed_rate": feature(0, "t/h"),
        "feed_grade": feature(0, "% Cu"), "recovery": feature(0, "%"),
        "concentrate_rate": feature(0, "t/h"), "tailings_rate": feature(0, "t/h"),
        "power_draw": feature(0, "MW"), "target_grade": feature(0.34, "% Cu")})
    result["substation-01"] = thing("substation-01", "Plant electrical substation", "substation", "area-utilities", {
        "coordinates": {"x": 83, "y": 77}, "available_mw": 75}, {
        "state": feature("normal"), "available_power": feature(75, "MW"),
        "plant_demand": feature(0, "MW"), "curtailment": feature(False)})
    result["maintenance-crew-01"] = thing("maintenance-crew-01", "Mobile maintenance crew", "maintenance-crew", "area-utilities", {
        "coordinates": {"x": 69, "y": 82}}, {"state": feature("available"), "active_job": feature("none"), "response_minutes": feature(8, "min")})
    result["dispatcher-01"] = thing("dispatcher-01", "Dispatch and blending control", "decision-service", "mine-01", {
        "coordinates": {"x": 65, "y": 12}}, {"scenario": feature("baseline"),
        "target_grade": feature(0.34, "% Cu"), "target_hardness": feature(12.8, "kWh/t"),
        "active_route": feature("road-main"), "last_decision": feature("Baseline dispatch active"),
        "decision_count": feature(0, "decisions")})
    # Schematic scene units: deliberately not a surveyed metric site map.
    scene_positions = {
        "phase-sulphide-01": [-37,-24,0], "face-west": [-46,-23,3], "face-east": [-29,-23,-8],
        "face-north": [-44,-23,-13], "face-waste": [-37,-23,7], "shovel-01": [-52,-22,1],
        "shovel-02": [-26,-22,-12], "rom-01": [40,0,29], "crusher-01": [59,0,5],
        "concentrator-01": [74,0,-30], "substation-01": [35,0,-39],
    }
    for name, body in result.items():
        body["attributes"].pop("coordinates", None)
        body["attributes"]["geometry_basis"] = "schematic scene units; equipment enlarged for readability"
        if name in scene_positions: body["attributes"]["scene_position"] = scene_positions[name]
    result["rom-01"]["attributes"]["feeds"] = f"{NS}:crusher-01"
    result["crusher-01"]["attributes"]["feeds"] = f"{NS}:concentrator-01"
    result["substation-01"]["attributes"]["supplies"] = [f"{NS}:crusher-01", f"{NS}:concentrator-01"]
    for face in ["face-west", "face-east", "face-north", "face-waste"]:
        result[face]["attributes"]["loaded_by"] = f"{NS}:shovel-02" if face == "face-east" else f"{NS}:shovel-01"
    for road in ["road-main", "road-north"]:
        result[road]["attributes"]["connects"] = [f"{NS}:phase-sulphide-01", f"{NS}:rom-01"]
    return {f"{NS}:{name}": body for name, body in result.items()}


def put(url, auth, tid, body):
    req = urllib.request.Request(f"{url}/api/2/things/{tid}", data=json.dumps(body).encode(), method="PUT",
        headers={"Authorization": auth, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.status


def main():
    url = os.environ.get("DITTO_URL", "http://localhost:8080").rstrip("/")
    password = os.environ["DITTO_PASSWORD"]
    auth = "Basic " + base64.b64encode(f"ditto:{password}".encode()).decode()
    for tid, body in twins().items():
        for attempt in range(20):
            try:
                status = put(url, auth, tid, body)
                print(f"{'created' if status == 201 else 'updated'} {tid}", flush=True)
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 19:
                    raise RuntimeError(f"Ditto twin setup failed for {tid}: {exc}") from exc
                time.sleep(2)
    print(f"{len(twins())} Aktogay twins ready", flush=True)


if __name__ == "__main__":
    main()
