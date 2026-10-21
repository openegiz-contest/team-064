import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import Mine,dispatch_experiment,FACES
from app import Runtime,telemetry
from setup_twins import twins

class ConstraintsTests(unittest.TestCase):
 def assert_balances(self,m):
  s=m.snapshot()
  for key in ('ore_balance_error','waste_balance_error','copper_balance_error','reserve_balance_error','processing_balance_error'):
   self.assertLess(abs(s[key]),1e-6,key)
 def test_finite_faces_deplete_and_idle_without_creating_material(self):
  m=Mine(dict(face_tonnes=225));m.step(28800)
  self.assertAlmostEqual(m.ore_mined,675,6)
  self.assertTrue(all(m.remaining[f]<1e-7 for f in FACES))
  self.assertTrue(any(t['state']=='waiting_for_resource' for t in m.trucks))
  before=m.ore_mined;m.apply_scenario('baseline');m.step(3600)
  self.assertEqual(before,m.ore_mined);self.assert_balances(m)
 def test_road_admission_enforces_headway_per_direction(self):
  m=Mine(dict(road_capacity=6));last={};observations=0
  for _ in range(2880):
   old={(r,d):m.road_entries[r][d] for r in m.road_entries for d in ('loaded','empty')}
   m.step(5)
   for key,prev in old.items():
    r,d=key
    if m.road_entries[r][d]>prev:
     if key in last:self.assertGreaterEqual(m.minute*60-last[key],600-1e-7)
     last[key]=m.minute*60;observations+=1
  self.assertGreater(observations,5);self.assertGreater(m.wait_seconds,0);self.assert_balances(m)
 def test_gradient_and_bucket_change_service(self):
  low=Mine(dict(main_grade=0));high=Mine(dict(main_grade=12))
  self.assertGreater(high.travel_seconds('road-main',True),low.travel_seconds('road-main',True))
  self.assertLess(high.travel_seconds('road-main',False),high.travel_seconds('road-main',True))
  small=Mine(dict(bucket_t=25));large=Mine(dict(bucket_t=65))
  for m in (small,large):
   for _ in range(200):
    m.step(5)
    if m.trucks[3]['state']=='loading':break
  self.assertGreater(small.trucks[3]['duration'],large.trucks[3]['duration'])
 def test_shovel_fault_holds_partial_load_then_recovers(self):
  m=Mine(dict(dispatch='rotation'))
  for _ in range(600):
   m.step(5)
   t=next((t for t in m.trucks if t['face']=='face-east' and t['state']=='loading' and t['payload']>1),None)
   if t:break
  self.assertIsNotNone(t);before=copy.deepcopy(t);reserve=m.remaining['face-east']
  m.apply_scenario('shovel-outage');m.step(600)
  self.assertEqual(t['payload'],before['payload']);self.assertEqual(m.remaining['face-east'],reserve)
  self.assertEqual(m.snapshot()['shovels'][1]['state'],'fault')
  m.apply_scenario('baseline');m.step(3600);self.assertGreater(t['trips'],before['trips']);self.assert_balances(m)
 def test_matched_experiment_nonmutating_and_reproducible(self):
  m=Mine();m.step(1200);before=copy.deepcopy(m.__dict__)
  a=dispatch_experiment(m,'low-grade',60);b=dispatch_experiment(m,'low-grade',60)
  self.assertEqual(a,b)
  self.assertEqual(m.snapshot(),MineSnapshot(before))
  self.assertEqual(m.rng.getstate(),before['rng'].getstate())
  for result in a['results'].values():self.assertLess(result['max_balance_error_t'],1e-6)
 def test_experiment_validation(self):
  for n in (0,481,60.5,True):
   with self.assertRaises(ValueError):dispatch_experiment(Mine(),minutes=n)
 def test_twins_and_resource_telemetry_agree(self):
  r=Runtime('standalone');r.mine.step(1800);s=r.capture();data=telemetry(s);definitions=twins()
  self.assertEqual(len(definitions),29)
  self.assertTrue(all('org.aktogay:'+n in definitions for n in data))
  for f in FACES:self.assertEqual(data[f]['available_tonnes']['properties']['value'],s['resources'][f]['remaining_t'])
  for sh in s['shovels']:self.assertEqual(data[sh['id']]['state']['properties']['value'],sh['state'])
  self.assertAlmostEqual(data['tailings-01']['received']['properties']['value']+s['concentrate_total'],s['processed'])
 def test_experiment_requires_pause_and_reset_clears_result(self):
  r=Runtime('standalone');r.command('start',{})
  with self.assertRaises(ValueError):r.command('experiment',{'minutes':30})
  r.command('pause',{});r.command('experiment',{'minutes':30})
  self.assertIsNotNone(r.state()['snapshot']['experiment']);r.command('reset',{})
  self.assertIsNone(r.state()['snapshot']['experiment'])

def MineSnapshot(state):
 m=Mine();m.__dict__=state;return m.snapshot()

if __name__=='__main__':unittest.main()
