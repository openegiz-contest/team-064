import copy,json,math,sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import Mine,validate,compare,SCENARIOS
from app import Runtime,telemetry,protocol

class ModelTests(unittest.TestCase):
 def balanced(self,m):
  s=m.snapshot()
  for k in ('ore_balance_error','waste_balance_error','copper_balance_error'):self.assertLess(abs(s[k]),1e-6,k)
  self.assertGreaterEqual(s['rom_t'],-1e-7);self.assertLessEqual(s['rom_t'],24000+1e-6)
  for t in s['trucks']:self.assertTrue(-1e-6<=t['payload']<=220+1e-6)
  self.assertLessEqual(m.concentrate_total,m.processed_cu/.25+1e-6)
 def test_eight_hour_baseline(self):
  m=Mine()
  for _ in range(96):m.step(300);self.balanced(m)
  self.assertGreater(m.processed,15000);self.assertTrue(all(t['trips']>0 for t in m.trucks))
 def test_scenarios_conserve_material(self):
  for case in SCENARIOS:
   with self.subTest(case=case['id']):
    m=Mine();m.step(3600);m.apply_scenario(case['id'])
    for _ in range(36):m.step(300);self.balanced(m)
 def test_power_cap_and_crusher_stop(self):
  m=Mine();m.step(600);m.apply_scenario('power-limit');m.step(60)
  self.assertAlmostEqual(m.last_feed,45000/21,6)
  p=m.processed;m.apply_scenario('crusher-outage');m.step(3600);self.assertEqual(m.processed,p);self.assertEqual(m.last_feed,0)
 def test_breakdown_freezes_payload_and_position(self):
  m=Mine();m.step(1100);m.apply_scenario('truck-breakdown');t=copy.deepcopy(m.trucks[2]);m.step(600)
  for k in ('position','payload','timer','cu'):self.assertEqual(t[k],m.trucks[2][k])
  m.apply_scenario('baseline');m.step(3600);self.assertGreater(m.trucks[2]['trips'],t['trips']);self.balanced(m)
 def test_route_closure_increases_next_trip_duration(self):
  m=Mine();m.apply_scenario('road-closure');found=False
  for _ in range(600):
   m.step(5)
   t=next((t for t in m.trucks if t['state']=='loaded_haul' and t['material']=='ore'),None)
   if t:self.assertEqual(t['route'],'road-north');self.assertAlmostEqual(t['duration'],m.travel_seconds('road-north',True));self.assertGreater(t['duration'],m.travel_seconds('road-main',True));found=True;break
  self.assertTrue(found)
 def test_grade_change_does_not_rewrite_loaded_ore(self):
  m=Mine();m.step(1200);before=copy.deepcopy(m.trucks);m.apply_scenario('low-grade')
  self.assertEqual(m.face_props['face-east']['grade'],.18)
  for a,b in zip(before,m.trucks):self.assertEqual(a['cu'],b['cu']);self.assertEqual(a['grade'],b['grade'])
 def test_counterfactual_is_reproducible_and_does_not_mutate(self):
  m=Mine();m.step(600);before=m.snapshot();a=compare(m,'crusher-outage');b=compare(m,'crusher-outage')
  self.assertEqual(a,b);self.assertEqual(before,m.snapshot());self.assertEqual(a['alternative']['processed_t'],0);self.assertGreater(a['baseline']['processed_t'],2500)
 def test_reproducible_seed(self):
  a=Mine();b=Mine();a.step(3000);b.step(3000);self.assertEqual(a.snapshot(),b.snapshot())
 def test_invalid_settings(self):
  for bad in [dict(fleet=9),dict(fleet=2.5),dict(fleet=True),dict(power_mw=float('nan')),dict(dispatch='invalid'),dict(unknown=2),dict(speed=0)]:
   with self.subTest(bad=bad),self.assertRaises(ValueError):validate(bad)
 def test_extreme_parameters_remain_balanced(self):
  for settings in [dict(fleet=2,power_mw=10),dict(load_minutes=3,haul_minutes=5,crusher_tph=500),dict(fleet=8,power_mw=90,crusher_tph=4500)]:
   m=Mine(settings);m.step(28800);self.balanced(m)

class RuntimeTests(unittest.TestCase):
 def test_ditto_topic_regression(self):
  p=protocol('mine-01',{'simulation_time':{'properties':{'value':1}}})
  self.assertEqual(p['topic'],'org.aktogay/mine-01/things/twin/commands/modify');self.assertNotIn(':',p['topic']);self.assertEqual(p['path'],'/features')
 def test_integrated_has_no_silent_local_fallback(self):
  r=Runtime('integrated');r.mine.step(600);r.publish();self.assertIsNone(r.state()['snapshot']);self.assertFalse(r.state()['transport']['fresh'])
 def test_atomic_snapshot_matches_numeric_twins(self):
  r=Runtime('standalone');r.mine.step(300);s=r.capture();t=telemetry(s);ui=json.loads(t['mine-01']['operator_state']['properties']['value'])
  self.assertEqual(ui['minute'],t['mine-01']['simulation_time']['properties']['value']);self.assertEqual(ui['feed_rate'],t['concentrator-01']['feed_rate']['properties']['value']);self.assertEqual(ui['events'],s['events'])
 def test_control_settings_and_reset(self):
  r=Runtime('standalone');r.publish();r.command('start',{});self.assertEqual(r.state()['snapshot']['status'],'running')
  with self.assertRaises(ValueError):r.command('settings',{'fleet':4})
  r.command('pause',{});r.command('settings',{'fleet':4,'power_mw':50});self.assertEqual(r.mine.settings['fleet'],4);self.assertEqual(r.status,'ready')
  r.command('start',{});r.mine.step(600);r.command('scenario',{'id':'power-limit'});r.command('reset',{})
  self.assertEqual(r.mine.minute,0);self.assertEqual(r.mine.active_scenario,'baseline');self.assertEqual(r.mine.settings['fleet'],4)
 def test_pause_holds_time(self):
  r=Runtime('standalone');r.start()
  try:
   r.command('start',{});time.sleep(.25);r.command('pause',{});minute=r.mine.minute;time.sleep(.25);self.assertEqual(minute,r.mine.minute)
  finally:r.stop.set()
 def test_stale_readback_is_not_live(self):
  r=Runtime('standalone');r.publish();r.verified['published_at']-=20;self.assertFalse(r.state()['transport']['fresh'])

if __name__=='__main__':unittest.main(verbosity=2)
