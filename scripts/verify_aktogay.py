#!/usr/bin/env python3
"""Checks the REAL running OpenEgiz stack. Exercises/reset simulation only, not Docker volumes."""
import base64,csv,io,json,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks=[]

def check(name,ok,detail=''):
 checks.append(dict(check=name,passed=bool(ok),detail=detail));print(('PASS ' if ok else 'FAIL ')+name+(' — '+detail if detail else ''),flush=True)
def req(url,data=None,headers=None):
 r=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),headers=headers or {'Content-Type':'application/json'})
 with urllib.request.urlopen(r,timeout=10) as response:return json.load(response)
def auth(user,password):return {'Authorization':'Basic '+base64.b64encode((user+':'+password).encode()).decode()}
def main():
 env={}
 for line in (ROOT/'deploy/compose/.env').read_text().splitlines():
  if '=' in line and not line.startswith('#'):k,v=line.split('=',1);env[k]=v
 base='http://127.0.0.1:'+env.get('AKTOGAY_PORT','8091')
 def wait(predicate,seconds=35):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   d=req(base+'/api/state');s=d.get('snapshot')
   if s and d['transport']['fresh'] and predicate(s):return s
   time.sleep(.7)
  raise RuntimeError('Confirmed snapshot condition timed out')
 def post(path,body):return req(base+path,body)
 state=req(base+'/api/state');check('UI reads integrated Eclipse Ditto state',state['transport']['mode']=='integrated' and state['transport']['source']=='eclipse-ditto' and state['transport']['fresh'])
 if not checks[-1]['passed']:raise RuntimeError('Integrated telemetry is required; local preview is not a Stand test')
 post('/api/reset',{});wait(lambda s:s['status']=='ready' and s['minute']==0)
 post('/api/control',{'action':'start'});first=wait(lambda s:s['minute']>0)
 second=wait(lambda s:s['minute']>first['minute']);check('Confirmed simulation clock advances',True)
 check('Normal operation produces feed',second['feed_rate']>0)
 ditto='http://127.0.0.1:'+env.get('DITTO_PORT','8080')
 thing=req(ditto+'/api/2/things/org.aktogay:mine-01?fields=features',headers=auth('ditto',env['DITTO_PASSWORD']))
 f=thing['features'];atomic=json.loads(f['operator_state']['properties']['value'])
 check('Atomic snapshot and numeric telemetry match',atomic['minute']==f['simulation_time']['properties']['value'] and atomic['feed_rate']==f['crusher_feed_rate']['properties']['value'])
 post('/api/control',{'action':'pause'});paused=wait(lambda s:s['status']=='paused');time.sleep(1.2);check('Pause holds simulation time',req(base+'/api/state')['snapshot']['minute']==paused['minute'])
 post('/api/control',{'action':'start'})
 tests={'crusher-outage':lambda s:s['crusher_state']=='fault' and s['feed_rate']==0,'truck-breakdown':lambda s:any(t['state']=='maintenance' for t in s['trucks']),
        'road-closure':lambda s:s['road_main_closed'],'power-limit':lambda s:s['available_mw']<=45 and s['feed_rate']<=45000/21+.01,
        'low-grade':lambda s:s['face_props']['face-east']['grade']==.18,'hard-ore':lambda s:s['face_props']['face-north']['hardness']==20,
        'shovel-outage':lambda s:any(x['id']=='shovel-02' and x['state']=='fault' for x in s['shovels']),
        'road-congestion':lambda s:s['roads']['road-main']['capacity_vph_per_lane']==12}
 for key,predicate in tests.items():
  post('/api/scenario',{'id':key});s=wait(lambda s:s['scenario']==key and predicate(s));check('Scenario '+key,True)
  check(key+' material balances',max(abs(s[k]) for k in ['ore_balance_error','waste_balance_error','copper_balance_error','reserve_balance_error','processing_balance_error'])<.01)
 post('/api/scenario',{'id':'baseline'});wait(lambda s:s['scenario']=='baseline')
 post('/api/compare',{'id':'power-limit'});wait(lambda s:s['comparison'] is not None);check('Paired forecast returns through Ditto',True)
 post('/api/control',{'action':'pause'});paused=wait(lambda s:s['status']=='paused')
 post('/api/experiment',{'id':'baseline','minutes':60});e=wait(lambda s:s.get('experiment') is not None)
 check('Matched dispatch experiment confirmed through Ditto',set(e['experiment']['results'])=={'rotation','adaptive'})
 check('Experiment preserves live clock',e['minute']==paused['minute'])
 for asset in ('waste-dump-01','tailings-01'):
  obj=req(ditto+'/api/2/things/org.aktogay:'+asset,headers=auth('ditto',env['DITTO_PASSWORD']))
  check('Accounting twin '+asset,obj.get('thingId')=='org.aktogay:'+asset and bool(obj.get('features')))
 post('/api/control',{'action':'start'})
 # Ensure the time-series pipeline receives current points, not an older run.
 start=time.time();influx='http://127.0.0.1:'+env.get('INFLUXDB_PORT','8086');found=False
 for _ in range(25):
  flux='from(bucket: "default") |> range(start: -45s) |> filter(fn: (r) => r.thingId == "org.aktogay:concentrator-01" and r._field == "value_feed_rate_properties_value") |> last()'
  request=urllib.request.Request(influx+'/api/v2/query?org=opentwins',data=flux.encode(),headers={'Authorization':'Token '+env['INFLUXDB_TOKEN'],'Content-Type':'application/vnd.flux','Accept':'application/csv'})
  with urllib.request.urlopen(request,timeout=10) as response:text=response.read().decode()
  rows=[r for r in csv.DictReader(line for line in text.splitlines() if line and not line.startswith('#')) if r.get('_value')]
  if rows:found=True;break
  time.sleep(2)
 check('Telegraf / InfluxDB stores recent Aktogay feed points',found)
 grafana='http://127.0.0.1:'+env.get('GRAFANA_PORT','3000');gh=auth('admin',env['GRAFANA_ADMIN_PASSWORD'])
 check('Grafana database healthy',req(grafana+'/api/health')['database']=='ok')
 dashboard=req(grafana+'/api/dashboards/uid/aktogay-shift-twin',headers=gh)
 check('Aktogay dashboard provisioned',dashboard['dashboard']['uid']=='aktogay-shift-twin')
 post('/api/reset',{});wait(lambda s:s['status']=='ready' and s['minute']==0);check('Reset returns ready baseline',True)

if __name__=='__main__':
 try:main()
 except Exception as e:check('Stand verification completed',False,str(e))
 out=ROOT/'docs/evidence/stand-report.json';out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(dict(checks=checks,passed=all(c['passed'] for c in checks),timestamp=time.time()),indent=2))
 print('Report:',out);sys.exit(0 if checks and all(c['passed'] for c in checks) else 1)
