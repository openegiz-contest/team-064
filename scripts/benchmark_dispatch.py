#!/usr/bin/env python3
"""Reproduce all policy outcomes; no cherry-picking or operational benefit claim."""
import hashlib,json,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'team/aktogay'))
from model import Mine,dispatch_experiment
def main():
 results=[]
 for scenario in ('baseline','low-grade','hard-ore','road-congestion','shovel-outage'):
  for seed in (7,23,64,101,2026):
   m=Mine(dict(seed=seed));r=dispatch_experiment(m,scenario,240);results.append(r)
 summary={}
 for condition in sorted(set(r['scenario'] for r in results)):
  cases=[r for r in results if r['scenario']==condition]
  summary[condition]={key:dict(mean=statistics.mean(r['delta'][key] for r in cases),
     min=min(r['delta'][key] for r in cases),max=max(r['delta'][key] for r in cases))
     for key in ('processed_t','grade_mae_pp','truck_wait_minutes','final_rom_t')}
 out=ROOT/'docs/evidence/dispatch-benchmark.json'
 out.write_text(json.dumps(dict(model_sha256=hashlib.sha256((ROOT/'team/aktogay/model.py').read_bytes()).hexdigest(),
    generated_at=time.time(),mode='pure model; no platform verification',horizon_minutes=240,
    seeds=[7,23,64,101,2026],summary=summary,runs=results),indent=2))
 print(json.dumps(summary,indent=2));print(out)
if __name__=='__main__':main()
