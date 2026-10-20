"""Seeded pit-to-plant model. Seconds internally; tonnes, % Cu and MW externally.
Synthetic engineering assumptions, not Aktogay operating records.
"""
import copy
import math
import random

DEFAULTS = dict(speed=60, fleet=8, crusher_tph=3200, power_mw=75, load_minutes=6.5,
                haul_minutes=9, target_grade=0.34, f1_grade=0.31, f2_grade=0.39,
                f3_grade=0.27, hardness=12.4, seed=64, dispatch='adaptive')
BOUNDS = dict(speed=(1,180), fleet=(2,8), crusher_tph=(500,4500), power_mw=(10,90),
              load_minutes=(3,12), haul_minutes=(5,20), target_grade=(0.15,0.8),
              f1_grade=(0.1,1), f2_grade=(0.1,1), f3_grade=(0.1,1), hardness=(8,24), seed=(0,999999))
SCENARIOS = [
 dict(id='crusher-outage',name='Crusher outage',short='CR-01 offline',description='Crushing stops. Trucks feed ROM until its finite capacity forces a queue.'),
 dict(id='truck-breakdown',name='Truck breakdown',short='HT-03 unavailable',description='A loaded or empty truck stops in place. Its payload is conserved; the remaining fleet continues.'),
 dict(id='road-closure',name='Main road closure',short='North route +45%',description='Committed trucks clear the main route; subsequent trips use the longer north haul road.'),
 dict(id='power-limit',name='Power curtailment',short='45 MW supply cap',description='Plant energy limits feed to at most 2,143 t/h, or less if the configured supply is lower.'),
 dict(id='low-grade',name='Low-grade pocket',short='F2 · 0.18% Cu',description='New F2 loads have lower grade. Ore already loaded retains its sampled quality.'),
 dict(id='hard-ore',name='Hard ore at F3',short='F3 · 20 kWh/t',description='New F3 loads are harder. Adaptive dispatch can avoid this face; feed response follows transport and blending delays.')]
ROM_CAPACITY=24000.0
ROM_INITIAL=8000.0
PAYLOAD=220.0
ENERGY=21.0
FACES=['face-west','face-east','face-north']


def validate(values):
    if not isinstance(values,dict):raise ValueError('Settings must be an object')
    unknown=set(values)-set(DEFAULTS)
    if unknown:raise ValueError('Unknown settings: '+', '.join(sorted(unknown)))
    result=dict(DEFAULTS,**values)
    for k,(lo,hi) in BOUNDS.items():
        v=result[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError(f'{k} must be between {lo} and {hi}')
        if k in ('fleet','seed') and int(v)!=v:raise ValueError(f'{k} must be an integer')
    if result['dispatch'] not in ('adaptive','rotation'):raise ValueError('Unknown dispatch policy')
    return result


class Mine:
    def __init__(self,settings=None):
        self.settings=validate(settings or {})
        self.rng=random.Random(self.settings['seed'])
        self.minute=0.0;self.active_scenario='baseline';self.events=[];self.event_seq=0
        self.ore_mined=0.0;self.waste_mined=0.0;self.waste_dumped=0.0
        self.processed=0.0;self.mined_cu=0.0;self.processed_cu=0.0;self.concentrate_total=0.0
        self.rom_t=ROM_INITIAL;self.rom_cu=ROM_INITIAL*0.0034
        self.rom_hardness=ROM_INITIAL*self.settings['hardness']
        self.last_feed=0.0;self.last_grade=0.34;self.last_hardness=self.settings['hardness']
        self.dispatch_count=0;self.last_decision='Ready for a new shift'
        self._conditions()
        self.trucks=[]
        for i in range(8):
            face=FACES[i%3]
            self.trucks.append(dict(id=f'truck-{i+1:02}',label=f'HT-{i+1:02}',
                state='empty_return' if i<self.settings['fleet'] else 'parked',
                timer=(i%4)*70.0,duration=self.settings['haul_minutes']*60*0.85,
                payload=0.0,cu=0.0,hardness_mass=0.0,grade=0.0,hardness=0.0,
                face=face,material='ore',route='road-main',position=1-(i%4)*70/(self.settings['haul_minutes']*60*0.85),
                speed=0.0,trips=0,reason='Initial empty return',saved_state=None))
        self.event('Shift ready. Initial ROM: 8,000 t at 0.34% Cu. Start Simulation to dispatch the fleet.')

    def _conditions(self):
        self.crusher_online=True;self.road_main_closed=False;self.broken_truck=None
        self.available_mw=self.settings['power_mw']
        self.face_props={f:dict(grade=self.settings[f'f{i+1}_grade'],hardness=self.settings['hardness']+d)
                         for i,(f,d) in enumerate(zip(FACES,[0.6,-0.9,2.6]))}

    def event(self,text):
        self.event_seq+=1
        self.events.insert(0,dict(id=self.event_seq,minute=round(self.minute,2),text=text))
        self.events=self.events[:40];self.last_decision=text

    def apply_scenario(self,key):
        if key not in [s['id'] for s in SCENARIOS]+['baseline']:raise ValueError('Unknown scenario')
        if self.broken_truck:
            t=next(t for t in self.trucks if t['id']==self.broken_truck)
            t['state']=t.pop('saved_state',None) or 'empty_return'
        self._conditions();self.active_scenario=key
        if key=='crusher-outage':self.crusher_online=False;self.last_feed=0
        if key=='power-limit':self.available_mw=min(45,self.settings['power_mw'])
        if key=='road-closure':self.road_main_closed=True
        if key=='truck-breakdown':
            t=next((t for t in self.trucks if t['id']=='truck-03' and t['state']!='parked'),self.trucks[0])
            self.broken_truck=t['id'];t['saved_state']=t['state'];t['state']='maintenance';t['speed']=0
        if key=='low-grade':self.face_props['face-east']['grade']=0.18
        if key=='hard-ore':self.face_props['face-north']['hardness']=20.0
        name=next((s['name'] for s in SCENARIOS if s['id']==key),'Normal operation')
        self.event(name+' applied. Existing material retains its sampled grade and hardness.')

    def shovel(self,face):return 1 if face=='face-east' else 0

    def assign(self,t):
        self.dispatch_count+=1
        waste=self.dispatch_count%11==0
        if waste:face='face-waste'
        elif self.settings['dispatch']=='rotation':face=FACES[(self.dispatch_count-1)%3]
        else:
            grade=self.rom_cu/self.rom_t*100 if self.rom_t else self.settings['target_grade']
            hardness=self.rom_hardness/self.rom_t if self.rom_t else self.settings['hardness']
            def score(f):
                q=sum(x['state'] in ('loading','queue_at_shovel') and self.shovel(x['face'])==self.shovel(f) for x in self.trucks if x is not t)
                p=self.face_props[f]
                g=(grade*min(self.rom_t,2000)+p['grade']*PAYLOAD)/(min(self.rom_t,2000)+PAYLOAD)
                return abs(g-self.settings['target_grade'])*40+max(0,p['hardness']-hardness)*0.025+q*0.055
            face=min(FACES,key=score)
        t.update(face=face,material='waste' if waste else 'ore',state='queue_at_shovel',timer=0,position=0,speed=0)
        t['reason']='Required waste movement' if waste else f"{self.settings['dispatch']} dispatch · target {self.settings['target_grade']:.2f}% Cu"
        self.event(f"{t['label']} → {face.replace('face-','').upper()}: {t['reason']}.")

    def _stage(self,t,state,duration):t.update(state=state,timer=0.0,duration=max(duration,1.0))

    def step(self,seconds):
        if not math.isfinite(seconds) or not 0<seconds<=86400:raise ValueError('Step must be in (0, 86400] seconds')
        # Bounded substeps keep throughput integration stable at every UI speed.
        left=seconds
        while left>1e-8:
            dt=min(5.0,left);left-=dt;self.minute+=dt/60
            for t in self.trucks:self._truck_step(t,dt)
            self._crush(dt)

    def _truck_step(self,t,dt):
        state=t['state']
        if state in ('parked','maintenance'):return
        if state=='queue_at_shovel':
            busy=any(x is not t and x['state']=='loading' and self.shovel(x['face'])==self.shovel(t['face']) for x in self.trucks)
            if busy:return
            self._stage(t,'loading',self.settings['load_minutes']*60*self.rng.uniform(.92,1.08))
            p=self.face_props.get(t['face'],dict(grade=0,hardness=0))
            t.update(grade=p['grade'],hardness=p['hardness'])
            return
        if state=='queue_at_crusher':
            if self.rom_t+t['payload']>ROM_CAPACITY or any(x['state']=='dumping' for x in self.trucks):return
            self._stage(t,'dumping',72);return
        dt=min(dt,max(0,t['duration']-t['timer']));t['timer']+=dt
        progress=min(1,t['timer']/t['duration'])
        if state=='loading':
            amount=min(PAYLOAD-t['payload'],PAYLOAD*dt/t['duration'])
            t['payload']+=amount;t['cu']+=amount*t['grade']/100;t['hardness_mass']+=amount*t['hardness']
            if t['material']=='ore':self.ore_mined+=amount;self.mined_cu+=amount*t['grade']/100
            else:self.waste_mined+=amount
        if state in ('loaded_haul','empty_return'):
            t['position']=progress if state=='loaded_haul' else 1-progress
            distance=2.5 if t['material']=='waste' else (5.2 if t['route']=='road-north' else 3.8)
            t['speed']=distance*3600/t['duration']
        if progress<1-1e-8:return
        if state=='loading':
            t['route']='road-north' if self.road_main_closed else 'road-main'
            duration=self.settings['haul_minutes']*60*(1.45 if t['route']=='road-north' else 1)
            self._stage(t,'loaded_haul',duration*(.65 if t['material']=='waste' else 1));t['position']=0
        elif state=='loaded_haul':
            t['speed']=0;t['position']=1
            self._stage(t,'dumping_waste' if t['material']=='waste' else 'queue_at_crusher',60)
        elif state in ('dumping','dumping_waste'):
            if t['material']=='ore':
                self.rom_t+=t['payload'];self.rom_cu+=t['cu'];self.rom_hardness+=t['hardness_mass']
            else:self.waste_dumped+=t['payload']
            t.update(payload=0,cu=0,hardness_mass=0,trips=t['trips']+1)
            t['route']='road-north' if self.road_main_closed else 'road-main'
            self._stage(t,'empty_return',self.settings['haul_minutes']*60*.85*(1.45 if t['route']=='road-north' else 1))
        elif state=='empty_return':self.assign(t)

    def _crush(self,dt):
        self.last_feed=0
        if not self.crusher_online or self.rom_t<1e-8:return
        grade=self.rom_cu/self.rom_t*100;hardness=self.rom_hardness/self.rom_t
        cap=min(self.settings['crusher_tph']*max(.52,1-max(0,hardness-12)*.045),self.available_mw*1000/ENERGY)
        amount=min(self.rom_t,cap*dt/3600);share=amount/self.rom_t
        cu=self.rom_cu*share
        self.rom_cu-=cu;self.rom_hardness*=1-share;self.rom_t-=amount
        self.processed+=amount;self.processed_cu+=cu
        recovery=self.recovery(grade,hardness)
        self.concentrate_total+=cu*recovery/.25
        self.last_feed=amount*3600/dt;self.last_grade=grade;self.last_hardness=hardness

    @staticmethod
    def recovery(grade,hardness):return max(.62,min(.94,.90-max(0,hardness-12)*.012+min(.025,max(0,grade-.30)*.10)))

    def snapshot(self):
        grade=self.rom_cu/self.rom_t*100 if self.rom_t>1e-8 else self.last_grade
        hardness=self.rom_hardness/self.rom_t if self.rom_t>1e-8 else self.last_hardness
        ore=sum(t['payload'] for t in self.trucks if t['material']=='ore')
        waste=sum(t['payload'] for t in self.trucks if t['material']=='waste')
        cu=sum(t['cu'] for t in self.trucks if t['material']=='ore')
        recovery=self.recovery(self.last_grade,self.last_hardness)
        trucks=copy.deepcopy(self.trucks)
        for t in trucks:t['stage_progress']=min(1,t['timer']/max(1,t['duration']))
        return dict(minute=self.minute,scenario=self.active_scenario,ore_mined=self.ore_mined,waste_mined=self.waste_mined,
            waste_dumped=self.waste_dumped,processed=self.processed,feed_rate=self.last_feed,grade=grade,hardness=hardness,
            recovery=recovery*100,concentrate_tph=self.last_feed*self.last_grade/100*recovery/.25,concentrate_total=self.concentrate_total,
            rom_t=self.rom_t,rom_pct=self.rom_t/ROM_CAPACITY*100,available_mw=self.available_mw,power_draw=self.last_feed*ENERGY/1000,
            ore_balance_error=ROM_INITIAL+self.ore_mined-self.processed-self.rom_t-ore,
            waste_balance_error=self.waste_mined-self.waste_dumped-waste,
            copper_balance_error=ROM_INITIAL*.0034+self.mined_cu-self.processed_cu-self.rom_cu-cu,
            trucks=trucks,events=copy.deepcopy(self.events),last_decision=self.last_decision,decision_count=self.dispatch_count,
            crusher_state='running' if self.crusher_online else 'fault',road_main_closed=self.road_main_closed,
            broken_truck=self.broken_truck,face_props=copy.deepcopy(self.face_props),settings=dict(self.settings),
            queue=sum(t['state']=='queue_at_crusher' for t in trucks),active_fleet=sum(t['state'] not in ('parked','maintenance') for t in trucks))


def compare(mine,scenario,minutes=60):
    """Paired forecasts from the same material inventory and RNG state; no mutation."""
    base=copy.deepcopy(mine);case=copy.deepcopy(mine)
    base.apply_scenario('baseline');case.apply_scenario(scenario)
    p0=mine.processed;c0=mine.concentrate_total
    points=[]
    for _ in range(minutes):
        base.step(60);case.step(60)
        if int(base.minute-mine.minute)%5==0:
            points.append(dict(minute=round(base.minute-mine.minute),baseline=round(base.last_feed),scenario=round(case.last_feed)))
    def summary(m):
        s=m.snapshot()
        return dict(processed_t=m.processed-p0,concentrate_t=m.concentrate_total-c0,rom_t=m.rom_t,feed_tph=s['feed_rate'],grade=s['grade'])
    return dict(scenario=scenario,horizon_minutes=minutes,start_minute=mine.minute,baseline=summary(base),alternative=summary(case),series=points,
                note='Paired synthetic forecast from the same current inventory and random state. Not a prediction of actual Aktogay performance.')
