#!/usr/bin/env python3
"""Aktogay control service. Integrated UI state is read back from Eclipse Ditto.
AKTOGAY_MODE=standalone is an explicitly labelled local development mode only.
"""
import base64
import copy
import json
import logging
import mimetypes
import os
import signal
import threading
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from model import Mine,DEFAULTS,SCENARIOS,validate,compare,dispatch_experiment

log=logging.getLogger('aktogay');NS='org.aktogay'
ROOT=Path(__file__).resolve().parent


def v(value,unit=None):return {'properties':dict(value=value,**({'unit':unit} if unit else {}))}


def telemetry(snapshot):
    """Full feature replacement retains platform time-series field naming."""
    s=snapshot;result={}
    result['mine-01']={k:v(s[field],unit) for k,field,unit in [
      ('ore_mined','ore_mined','t'),('waste_mined','waste_mined','t'),('crusher_feed_rate','feed_rate','t/h'),
      ('feed_grade','grade','% Cu'),('feed_hardness','hardness','kWh/t'),('copper_recovery','recovery','%'),
      ('concentrate_rate','concentrate_tph','t/h'),('mass_balance_error','ore_balance_error','t'),('simulation_time','minute','min')]}
    # One atomic snapshot prevents mixed revisions/times across UI widgets.
    result['mine-01'].update(scenario=v(s['scenario']),operator_state=v(json.dumps(s,separators=(',',':'))),
                            sequence=v(s['sequence']),run_id=v(s['run_id']),simulation_status=v(s['status']))
    for name,p in s['face_props'].items():
        resource=s['resources'][name]
        result[name]={'grade':v(p['grade'],'% Cu'),'hardness':v(p['hardness'],'kWh/t'),'material':v('ore'),
            'available_tonnes':v(resource['remaining_t'],'t'),'state':v(resource['state'])}
    result['face-waste']={'grade':v(0,'% Cu'),'material':v('waste'),'available_tonnes':v(s['resources']['face-waste']['remaining_t'],'t')}
    for route in ['road-main','road-north']:
        closed=route=='road-main' and s['road_main_closed']
        result[route]={'state':v('closed; committed trips clearing' if closed else 'open'),'closed':v(closed),
                       'occupancy':v(s['roads'][route]['occupancy'],'trucks'),
                       'waiting':v(s['roads'][route]['queue'],'trucks'),
                       'capacity_per_lane':v(s['roads'][route]['capacity_vph_per_lane'],'vehicles/h'),
                       'gradient':v(s['roads'][route]['gradient_pct'],'%'),
                       'admitted_loaded':v(s['roads'][route]['entries']['loaded'],'vehicles')}
    for t in s['trucks']:
        result[t['id']]={'state':v(t['state']),'payload':v(t['payload'],'t'),'material':v(t['material']),
           'assigned_face':v(t['face']),'destination':v('waste dump' if t['material']=='waste' else 'ROM stockpile'),
           'speed':v(t['speed'],'km/h'),'route_position':v(t['position'],'ratio'),'route':v(t['route']),
           'trips_total':v(t['trips'],'trips'),'dispatch_reason':v(t['reason']),'waiting_time':v(t['wait_seconds']/60,'min')}
    for shovel in s['shovels']:
        result[shovel['id']]={'state':v(shovel['state']),'payload_rate':v(shovel['payload_rate'],'t/h'),
            'assigned_face':v(shovel['face'] or 'none'),'truck':v(shovel['truck'] or 'none'),
            'utilization':v(shovel['utilization_pct'],'%'),'bucket_capacity':v(shovel['bucket_t'],'t')}
    result['waste-dump-01']={'received':v(s['waste_dumped'],'t')}
    result['tailings-01']={'received':v(s['metrics']['tailings_t'],'t'),'contained_copper':v(s['processed_cu']-s['metrics']['recovered_cu_t'],'t Cu')}
    result['rom-01']={'level':v(s['rom_t'],'t'),'fill_pct':v(s['rom_pct'],'%'),'grade':v(s['grade'],'% Cu'),'hardness':v(s['hardness'],'kWh/t')}
    result['crusher-01']={'state':v(s['crusher_state']),'throughput':v(s['feed_rate'],'t/h'),'feed_grade':v(s['grade'],'% Cu'),
                         'feed_hardness':v(s['hardness'],'kWh/t'),'tonnes_total':v(s['processed'],'t'),'power_draw':v(s['power_draw']*8/21,'MW')}
    result['concentrator-01']={'state':v('running' if s['feed_rate'] else 'no feed'),'feed_rate':v(s['feed_rate'],'t/h'),
        'feed_grade':v(s['grade'],'% Cu'),'recovery':v(s['recovery'],'%'),'concentrate_rate':v(s['concentrate_tph'],'t/h'),
        'power_draw':v(s['power_draw']*13/21,'MW'),'target_grade':v(s['settings']['target_grade'],'% Cu')}
    result['substation-01']={'available_power':v(s['available_mw'],'MW'),'plant_demand':v(s['power_draw'],'MW'),
                            'state':v('curtailed' if s['scenario']=='power-limit' else 'normal')}
    result['maintenance-crew-01']={'state':v('working' if s['broken_truck'] else 'available'),'active_job':v(s['broken_truck'] or 'none')}
    result['dispatcher-01']={'scenario':v(s['scenario']),'last_decision':v(s['last_decision']),
        'decision_count':v(s['decision_count']),'target_grade':v(s['settings']['target_grade'],'% Cu'),
        'active_route':v('road-north' if s['road_main_closed'] else 'road-main'),'policy':v(s['settings']['dispatch'])}
    return result


def protocol(name,features):
    # Ditto protocol has namespace/name, NOT namespace:name (REST thing ID).
    return {'topic':f'{NS}/{name}/things/twin/commands/modify','path':'/features','value':features}


class Runtime:
    def __init__(self,mode=None):
        self.mode=mode or os.getenv('AKTOGAY_MODE','integrated')
        if self.mode not in ('integrated','standalone'):raise ValueError('Invalid AKTOGAY_MODE')
        settings=dict(DEFAULTS,speed=float(os.getenv('SIM_SPEEDUP','60')),seed=int(os.getenv('SIM_SEED','64')))
        self.mine=Mine(settings);self.publish_lock=threading.Lock();self.lock=threading.RLock();self.stop=threading.Event();self.connected=False
        self.status='ready';self.sequence=0;self.run_id=uuid.uuid4().hex[:12]
        self.history=[];self.comparison=None;self.experiment=None;self.experiment_lock=threading.Lock();self.verified=None;self.verified_at=0.0
        self.last_publish=0.0;self.last_error='Waiting for platform telemetry' if self.mode=='integrated' else None
        self.mqtt=None;self.last_snapshot=None
        self.ditto_url=os.getenv('DITTO_URL','http://localhost:8080').rstrip('/')
        password=os.getenv('DITTO_PASSWORD','')
        self.auth='Basic '+base64.b64encode(('ditto:'+password).encode()).decode()

    def capture(self):
        with self.lock:
            self.sequence+=1;s=self.mine.snapshot()
            s.update(sequence=self.sequence,run_id=self.run_id,status=self.status,published_at=time.time(),
                     history=copy.deepcopy(self.history),comparison=copy.deepcopy(self.comparison),experiment=copy.deepcopy(self.experiment))
            self.last_snapshot=s
            return s

    def publish(self):
        with self.publish_lock:self._publish()

    def _publish(self):
        s=self.capture()
        if self.mode=='standalone':
            with self.lock:self.verified=s;self.verified_at=time.time();self.last_error=None
            return
        if not self.connected or not self.mqtt:return
        features=telemetry(s)
        # Aggregate last: its atomic operator snapshot is the UI read model.
        for name in list(n for n in features if n!='mine-01')+['mine-01']:
            info=self.mqtt.publish('telemetry/'+name,json.dumps(protocol(name,features[name])),qos=1,retain=False)
            if info.rc!=0:self.last_error='MQTT publish rejected';return
        self.last_publish=time.time()

    def readback(self):
        while not self.stop.is_set():
            try:
                req=urllib.request.Request(self.ditto_url+'/api/2/things/org.aktogay:mine-01?fields=features',headers={'Authorization':self.auth})
                with urllib.request.urlopen(req,timeout=3) as response:thing=json.load(response)
                s=json.loads(thing['features']['operator_state']['properties']['value'])
                if s['run_id']!=self.run_id:raise ValueError('Waiting for this run to reach Ditto')
                with self.lock:
                    if self.verified is None or s['sequence']>=self.verified['sequence']:
                        self.verified=s;self.verified_at=time.time();self.last_error=None
            except Exception as e:
                self.last_error=f'Ditto readback: {type(e).__name__}: {e}'
            self.stop.wait(.7)

    def start(self):
        if self.mode=='integrated':
            import paho.mqtt.client as mqtt
            self.mqtt=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='aktogay-'+self.run_id)
            self.mqtt.on_connect=lambda c,u,f,rc,p:setattr(self,'connected',rc==0)
            self.mqtt.on_disconnect=lambda c,u,f,rc,p:setattr(self,'connected',False)
            self.mqtt.reconnect_delay_set(1,10)
            self.mqtt.connect_async(os.getenv('MQTT_HOST','mosquitto'),int(os.getenv('MQTT_PORT','1883')),30)
            self.mqtt.loop_start()
            threading.Thread(target=self.readback,daemon=True).start()
        self.publish()
        threading.Thread(target=self.loop,daemon=True).start()

    def loop(self):
        last=time.monotonic();last_pub=0
        while not self.stop.wait(.1):
            now=time.monotonic();elapsed=min(1,now-last);last=now
            try:
                with self.lock:
                    if self.status=='running':
                        self.mine.step(elapsed*self.mine.settings['speed'])
                        if not self.history or self.mine.minute-self.history[-1]['minute']>=1:
                            s=self.mine.snapshot();self.history.append({k:round(s[k],3) for k in ('minute','feed_rate','grade','rom_t','power_draw')});self.history=self.history[-120:]
                if now-last_pub>=.7:self.publish();last_pub=now
            except Exception:
                log.exception('Simulation cycle failed')
                with self.lock:self.status='error';self.last_error='Simulation error; inspect service logs'

    def state(self):
        with self.lock:
            s=copy.deepcopy(self.verified)
            age=time.time()-s['published_at'] if s else None
            fresh=age is not None and age<6 and (self.mode=='standalone' or self.connected)
            return dict(snapshot=s,transport=dict(mode=self.mode,source='local-model' if self.mode=='standalone' else 'eclipse-ditto',
              fresh=fresh,age_s=round(age,2) if age is not None else None,mqtt=self.connected,
              error=self.last_error,requested_sequence=self.sequence),server_time=time.time())

    def command(self,action,data):
        if not isinstance(data,dict):raise ValueError('JSON body must be an object')
        if action=='compare':
            with self.lock:source_mine=self.mine;m=copy.deepcopy(self.mine)
            scenario=data.get('id','power-limit')
            result=compare(m,scenario)
            with self.lock:
                if self.mine is not source_mine:raise ValueError('Shift changed during forecast; run it again')
                self.comparison=result;self.mine.event(f"60-minute paired forecast completed: {scenario}.")
        elif action=='experiment':
            if not self.experiment_lock.acquire(blocking=False):raise ValueError('An experiment is already running')
            try:
                with self.lock:
                    if self.status=='running':raise ValueError('Pause the shift before comparing dispatch policies')
                    source_mine=self.mine;m=copy.deepcopy(self.mine)
                result=dispatch_experiment(m,data.get('id','baseline'),data.get('minutes',240))
                with self.lock:
                    if self.mine is not source_mine:raise ValueError('Shift changed during experiment; run it again')
                    self.experiment=result;self.mine.event('Matched dispatch comparison completed; inspect trade-offs.')
            finally:self.experiment_lock.release()
        else:
            with self.lock:
                if action in ('start','resume'):
                    self.status='running';self.mine.event('Simulation running.')
                elif action=='pause':self.status='paused';self.mine.event('Simulation paused. All material and equipment states held.')
                elif action=='reset':
                    self.mine=Mine(self.mine.settings);self.status='ready';self.history=[];self.comparison=None;self.experiment=None
                elif action=='settings':
                    if self.status=='running':raise ValueError('Pause the simulation before applying model settings')
                    settings=validate(dict(self.mine.settings,**data))
                    self.mine=Mine(settings);self.status='ready';self.history=[];self.comparison=None;self.experiment=None
                    self.mine.event('Validated settings applied. New shift ready.')
                elif action=='speed':
                    settings=validate(dict(self.mine.settings,speed=data.get('speed')))
                    self.mine.settings['speed']=settings['speed']
                elif action=='scenario':
                    if self.status!='running':raise ValueError('Start or resume the simulation before applying a scenario')
                    self.mine.apply_scenario(data.get('id',''))
                else:raise ValueError('Unknown control action')
        self.publish()
        return dict(ok=True,accepted=True,sequence=self.sequence,message='Command accepted; awaiting confirmed telemetry' if self.mode=='integrated' else 'Command applied')


runtime=None

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):log.debug(fmt,*args)
    def json(self,code,value):
        body=json.dumps(value,allow_nan=False,separators=(',',':')).encode();self.send_response(code)
        self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/state':return self.json(200,runtime.state())
        if path=='/api/scenarios':return self.json(200,dict(scenarios=SCENARIOS,defaults=DEFAULTS))
        if path=='/healthz':
            state=runtime.state();ok=state['transport']['fresh']
            return self.json(200 if ok else 503,dict(ok=ok,**state['transport']))
        if path=='/' or path=='/index.html':file=ROOT/'index.html'
        elif path.startswith('/static/'):
            file=(ROOT/urllib.parse.unquote(path.lstrip('/'))).resolve()
            if not file.is_relative_to(ROOT/'static'):return self.json(403,dict(error='Forbidden'))
        else:return self.json(404,dict(error='Not found'))
        if not file.is_file():return self.json(404,dict(error='File not found'))
        body=file.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(file)[0] or 'application/octet-stream')
        self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=8192:raise ValueError('Request too large')
            data=json.loads(self.rfile.read(length) or '{}')
            if not isinstance(data,dict):raise ValueError('JSON body must be an object')
            actions={'/api/control':data.get('action'),'/api/scenario':'scenario','/api/reset':'reset','/api/settings':'settings','/api/compare':'compare','/api/experiment':'experiment'}
            if self.path not in actions:return self.json(404,dict(error='Not found'))
            self.json(200,runtime.command(actions[self.path],data))
        except (ValueError,TypeError) as e:self.json(400,dict(error=str(e)))
        except Exception:log.exception('Control failed');self.json(500,dict(error='Control failed; inspect service logs'))


def main():
    global runtime
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    runtime=Runtime();runtime.start()
    server=ThreadingHTTPServer((os.getenv('WEB_BIND','0.0.0.0'),int(os.getenv('WEB_PORT','8088'))),Handler)
    def shutdown(*args):runtime.stop.set();threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown);signal.signal(signal.SIGINT,shutdown)
    log.info('Aktogay 3D ready; mode=%s; simulation awaits Start',runtime.mode)
    server.serve_forever();server.server_close()
    if runtime.mqtt:runtime.mqtt.loop_stop()

if __name__=='__main__':main()
