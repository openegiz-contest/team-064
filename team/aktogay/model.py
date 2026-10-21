"""Seeded pit-to-plant model. Seconds internally; tonnes, % Cu and MW externally.
Synthetic engineering assumptions, not Aktogay operating records.
"""
import copy
import math
import random
import hashlib

DEFAULTS = dict(speed=60, fleet=8, crusher_tph=3200, power_mw=75, load_minutes=6.5,
                haul_minutes=9, target_grade=0.34, f1_grade=0.31, f2_grade=0.39,
                f3_grade=0.27, hardness=12.4, seed=64, dispatch='adaptive', face_tonnes=85000, road_capacity=36,
                main_grade=6, north_grade=8, bucket_t=45)
BOUNDS = dict(speed=(1,180), fleet=(2,8), crusher_tph=(500,4500), power_mw=(10,90),
              load_minutes=(3,12), haul_minutes=(5,20), target_grade=(0.15,0.8),
              f1_grade=(0.1,1), f2_grade=(0.1,1), f3_grade=(0.1,1), hardness=(8,24), seed=(0,999999),
              face_tonnes=(220,150000), road_capacity=(6,60), main_grade=(0,12),
              north_grade=(0,12), bucket_t=(25,65))
SCENARIOS = [
 dict(id='crusher-outage',name='Crusher outage',short='CR-01 offline',description='Crushing stops. Trucks feed ROM until its finite capacity forces a queue.'),
 dict(id='truck-breakdown',name='Truck breakdown',short='HT-03 unavailable',description='A loaded or empty truck stops in place. Its payload is conserved; the remaining fleet continues.'),
 dict(id='road-closure',name='Main road closure',short='Longer north route',description='Committed trucks clear the main route; subsequent trips use the longer north haul road. Distance and gradient set travel time.'),
 dict(id='power-limit',name='Power curtailment',short='45 MW supply cap',description='Plant energy limits feed to at most 2,143 t/h, or less if the configured supply is lower.'),
 dict(id='low-grade',name='Low-grade pocket',short='F2 · 0.18% Cu',description='New F2 loads have lower grade. Ore already loaded retains its sampled quality.'),
 dict(id='hard-ore',name='Hard ore at F3',short='F3 · 20 kWh/t',description='New F3 loads are harder. Adaptive dispatch can avoid this face; feed response follows transport and blending delays.'),
 dict(id='shovel-outage',name='Shovel SH-02 outage',short='F2 loading interrupted',description='SH-02 stops. A partial load is held; dispatch redirects new trucks to other available faces.'),
 dict(id='road-congestion',name='Road entry restriction',short='Main road: 12 vehicles/h/lane',description='Entry headway increases on both main-road lanes. Trucks queue before admission; trips already on the road continue.')]
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
        self.reserve_initial={**{f:float(self.settings['face_tonnes']) for f in FACES},'face-waste':120000.0}
        self.remaining=dict(self.reserve_initial)
        self.road_next={r:{d:0.0 for d in ('loaded','empty')} for r in ('road-main','road-north')}
        self.road_entries={r:{d:0 for d in ('loaded','empty')} for r in self.road_next}
        self.shovel_seconds=[0.0,0.0];self.wait_seconds=0.0;self.energy_kwh=0.0
        self.grade_error_mass=0.0;self.starved_minutes=0.0;self.tailings_total=0.0;self.recovered_cu=0.0
        self.last_dispatch=None;self.scenario_started=0.0;self.scenario_reference=None
        self._conditions()
        self.trucks=[]
        for i in range(8):
            face=FACES[i%3]
            self.trucks.append(dict(id=f'truck-{i+1:02}',label=f'HT-{i+1:02}',
                state='empty_return' if i<self.settings['fleet'] else 'parked',
                timer=(i%4)*70.0,duration=self.settings['haul_minutes']*60*0.85,
                payload=0.0,cu=0.0,hardness_mass=0.0,grade=0.0,hardness=0.0,
                face=face,material='ore',route='road-main',position=1-(i%4)*70/(self.settings['haul_minutes']*60*0.85),
                speed=0.0,trips=0,reason='Initial empty return',saved_state=None,
                load_count=0,load_target=PAYLOAD,wait_seconds=0.0,wait_since=0.0,decision=None))
        for t in self.trucks:
            t['duration']=self.travel_seconds('road-main',False)
            t['timer']=min(t['timer'],t['duration']*.9)
            t['position']=1-t['timer']/t['duration']
        self.event('Shift ready. Initial ROM: 8,000 t at 0.34% Cu. Start Simulation to dispatch the fleet.')

    def _conditions(self):
        self.crusher_online=True;self.road_main_closed=False;self.broken_truck=None
        self.available_mw=self.settings['power_mw'];self.shovel_online=[True,True]
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
        self.scenario_reference={'minute':self.minute,'processed':self.processed,'rom_t':self.rom_t,
                                 'grade':self.rom_cu/self.rom_t*100 if self.rom_t else self.last_grade}
        self.scenario_started=self.minute
        self._conditions();self.active_scenario=key
        if key=='crusher-outage':self.crusher_online=False;self.last_feed=0
        if key=='power-limit':self.available_mw=min(45,self.settings['power_mw'])
        if key=='road-closure':self.road_main_closed=True
        if key=='truck-breakdown':
            t=next((t for t in self.trucks if t['id']=='truck-03' and t['state']!='parked'),self.trucks[0])
            self.broken_truck=t['id'];t['saved_state']=t['state'];t['state']='maintenance';t['speed']=0
        if key=='low-grade':self.face_props['face-east']['grade']=0.18
        if key=='hard-ore':self.face_props['face-north']['hardness']=20.0
        if key=='shovel-outage':self.shovel_online[1]=False
        name=next((s['name'] for s in SCENARIOS if s['id']==key),'Normal operation')
        self.event(name+' applied. Existing material retains its sampled grade and hardness.')

    def shovel(self,face):return 1 if face=='face-east' else 0

    def available_faces(self):
        return [f for f in FACES if self.remaining[f]>1e-8 and self.shovel_online[self.shovel(f)]]

    def assign(self,t):
        faces=self.available_faces()
        waste=(self.dispatch_count+1)%11==0 and self.remaining['face-waste']>1e-8 and self.shovel_online[0]
        if not faces and not waste:
            t.update(state='waiting_for_resource',speed=0,position=0,reason='No available ore face/shovel')
            return
        self.dispatch_count+=1
        candidates=[]
        if waste:face='face-waste'
        elif self.settings['dispatch']=='rotation':face=faces[(self.dispatch_count-1)%len(faces)]
        else:
            # All material already committed to ROM, including loaded trucks.
            mass=self.rom_t+sum(x['payload'] for x in self.trucks if x['material']=='ore')
            copper=self.rom_cu+sum(x['cu'] for x in self.trucks if x['material']=='ore')
            for f in faces:
                prop=self.face_props[f];payload=min(PAYLOAD,self.remaining[f])
                projected=(copper+payload*prop['grade']/100)/max(1,mass+payload)*100
                q=sum(x is not t and x['state'] in ('loading','queue_at_shovel') and self.shovel(x['face'])==self.shovel(f) for x in self.trucks)
                grade_penalty=abs(projected-self.settings['target_grade'])*40
                queue_penalty=q*.10
                hard_penalty=max(0,prop['hardness']-self.settings['hardness'])*.025
                candidates.append(dict(face=f,projected_grade=projected,queue_trucks=q,
                    grade_penalty=grade_penalty,queue_penalty=queue_penalty,hardness_penalty=hard_penalty,
                    score=grade_penalty+queue_penalty+hard_penalty))
            face=min(candidates,key=lambda c:c['score'])['face']
        t.update(face=face,material='waste' if waste else 'ore',state='queue_at_shovel',timer=0,position=0,speed=0,wait_since=self.minute*60)
        t['decision']=dict(minute=self.minute,truck=t['id'],policy=self.settings['dispatch'],chosen=face,candidates=candidates)
        self.last_dispatch=copy.deepcopy(t['decision'])
        t['reason']='Required waste movement' if waste else f"{self.settings['dispatch']} dispatch; target {self.settings['target_grade']:.2f}% Cu"
        self.event(f"{t['label']} to {face}: {t['reason']}.")

    def route_capacity(self,route):
        return min(self.settings['road_capacity'],12) if route=='road-main' and self.active_scenario=='road-congestion' else self.settings['road_capacity']

    def travel_seconds(self,route,loaded,material='ore'):
        # Synthetic average-speed law, not a manufacturer's truck performance curve.
        distance=2.5 if material=='waste' else (5.2 if route=='road-north' else 3.8)
        grade=self.settings['north_grade'] if route=='road-north' else self.settings['main_grade']
        flat_speed=3.8/(self.settings['haul_minutes']/60)*1.30
        speed=flat_speed/(1+.05*grade) if loaded else flat_speed/(.85*(1+.05*grade))
        speed=min(45 if loaded else 50,speed)
        return distance/speed*3600

    def queue_road(self,t,loaded):
        t.update(state='queue_road_loaded' if loaded else 'queue_road_empty',
                 route='road-north' if self.road_main_closed else 'road-main',
                 wait_since=self.minute*60,speed=0,position=0 if loaded else 1)

    def admit_road(self,t):
        loaded=t['state']=='queue_road_loaded';direction='loaded' if loaded else 'empty'
        route='road-north' if self.road_main_closed else 'road-main';t['route']=route
        now=self.minute*60
        queue=[x for x in self.trucks if x['state']==t['state']]
        first=min(queue,key=lambda x:(x['wait_since'],x['id']))
        if first is not t or now+1e-8<self.road_next[route][direction]:return
        self.road_next[route][direction]=now+3600/self.route_capacity(route)
        self.road_entries[route][direction]+=1
        self._stage(t,'loaded_haul' if loaded else 'empty_return',self.travel_seconds(route,loaded,t['material']))

    def waiting(self,t,dt):
        self.wait_seconds+=dt;t['wait_seconds']+=dt

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
        if state=='waiting_for_resource':
            self.waiting(t,dt)
            if self.available_faces():self.assign(t)
            return
        if state in ('queue_road_loaded','queue_road_empty'):
            self.waiting(t,dt);self.admit_road(t);return
        if state=='queue_at_shovel':
            self.waiting(t,dt)
            if self.remaining[t['face']]<=1e-8 or not self.shovel_online[self.shovel(t['face'])]:
                self.assign(t);return
            busy=any(x is not t and (x['state']=='loading' or (x['state']=='maintenance' and x.get('saved_state')=='loading'))
                     and self.shovel(x['face'])==self.shovel(t['face']) for x in self.trucks)
            queue=[x for x in self.trucks if x['state']=='queue_at_shovel' and self.shovel(x['face'])==self.shovel(t['face'])]
            if busy or min(queue,key=lambda x:(x['wait_since'],x['id'])) is not t:return
            t['load_count']+=1;t['load_target']=min(PAYLOAD,self.remaining[t['face']])
            passes=math.ceil(t['load_target']/(self.settings['bucket_t']*.9))
            key=f"{self.settings['seed']}:{t['id']}:{t['load_count']}".encode()
            variation=.92+int.from_bytes(hashlib.sha256(key).digest()[:4],'big')/(2**32-1)*.16
            self._stage(t,'loading',passes*self.settings['load_minutes']*60/6*variation)
            prop=self.face_props.get(t['face'],dict(grade=0,hardness=0))
            t.update(grade=prop['grade'],hardness=prop['hardness'])
            return
        if state=='queue_at_crusher':
            self.waiting(t,dt)
            busy=any(x['state']=='dumping' or (x['state']=='maintenance' and x.get('saved_state')=='dumping') for x in self.trucks)
            if self.rom_t+t['payload']>ROM_CAPACITY or busy:return
            self._stage(t,'dumping',72);return
        if state=='loading' and not self.shovel_online[self.shovel(t['face'])]:
            self.waiting(t,dt);return
        dt=min(dt,max(0,t['duration']-t['timer']));t['timer']+=dt
        progress=min(1,t['timer']/t['duration'])
        if state=='loading':
            amount=min(t['load_target']-t['payload'],t['load_target']*dt/t['duration'],self.remaining[t['face']])
            self.remaining[t['face']]=max(0,self.remaining[t['face']]-amount)
            self.shovel_seconds[self.shovel(t['face'])]+=dt
            if self.remaining[t['face']]<=1e-8 and amount>0:self.event(t['face']+' depleted; future trucks need another face.')
            t['payload']+=amount;t['cu']+=amount*t['grade']/100;t['hardness_mass']+=amount*t['hardness']
            if t['material']=='ore':self.ore_mined+=amount;self.mined_cu+=amount*t['grade']/100
            else:self.waste_mined+=amount
        if state in ('loaded_haul','empty_return'):
            t['position']=progress if state=='loaded_haul' else 1-progress
            distance=2.5 if t['material']=='waste' else (5.2 if t['route']=='road-north' else 3.8)
            t['speed']=distance*3600/t['duration']
        if progress<1-1e-8:return
        if state=='loading':self.queue_road(t,True)
        elif state=='loaded_haul':
            t['speed']=0;t['position']=1
            self._stage(t,'dumping_waste' if t['material']=='waste' else 'queue_at_crusher',60)
        elif state in ('dumping','dumping_waste'):
            if t['material']=='ore':
                self.rom_t+=t['payload'];self.rom_cu+=t['cu'];self.rom_hardness+=t['hardness_mass']
            else:self.waste_dumped+=t['payload']
            t.update(payload=0,cu=0,hardness_mass=0,trips=t['trips']+1)
            self.queue_road(t,False)
        elif state=='empty_return':self.assign(t)

    def _crush(self,dt):
        self.last_feed=0
        if not self.crusher_online or self.rom_t<1e-8:
            self.starved_minutes+=dt/60;return
        grade=self.rom_cu/self.rom_t*100;hardness=self.rom_hardness/self.rom_t
        cap=min(self.settings['crusher_tph']*max(.52,1-max(0,hardness-12)*.045),self.available_mw*1000/ENERGY)
        amount=min(self.rom_t,cap*dt/3600);share=amount/self.rom_t
        cu=self.rom_cu*share
        self.rom_cu-=cu;self.rom_hardness*=1-share;self.rom_t-=amount
        self.processed+=amount;self.processed_cu+=cu
        recovery=self.recovery(grade,hardness)
        concentrate=cu*recovery/.25
        self.concentrate_total+=concentrate;self.tailings_total+=amount-concentrate
        self.recovered_cu+=cu*recovery;self.energy_kwh+=amount*ENERGY
        self.grade_error_mass+=amount*abs(grade-self.settings['target_grade'])
        self.last_feed=amount*3600/dt;self.last_grade=grade;self.last_hardness=hardness
        if self.last_feed<.8*self.settings['crusher_tph']:self.starved_minutes+=dt/60

    @staticmethod
    def recovery(grade,hardness):return max(.62,min(.94,.90-max(0,hardness-12)*.012+min(.025,max(0,grade-.30)*.10)))

    def impact(self):
        chains={
            'baseline':['Available faces and shovels','Truck loading and road admission','ROM mixing','Concentrator feed'],
            'crusher-outage':['Crusher unavailable','Processing stops immediately','ROM stores arriving ore','Full ROM blocks dumping'],
            'truck-breakdown':['Truck held with its payload','Fleet availability decreases','Ore arrivals change','ROM buffers feed impact'],
            'road-closure':['Main road closed to new entries','Committed trips clear','New trips use north route','Longer cycles affect arrivals'],
            'power-limit':['Supply capped','Energy constrains processing','Feed and demand fall','ROM inventory responds'],
            'low-grade':['New F2 loads at 0.18% Cu','Existing loads unchanged','Travel and ROM mixing delay response','Feed quality changes'],
            'hard-ore':['New F3 loads at 20 kWh/t','Dispatch may avoid F3','Loaded material reaches ROM','Hardness limits processing'],
            'shovel-outage':['SH-02 unavailable','Partial load held','New assignments use SH-01','Loading queues and arrivals change'],
            'road-congestion':['Main road admission restricted','Waiting trucks form a queue','Trips already admitted continue','Ore arrivals slow']}
        return dict(chain=chains[self.active_scenario],elapsed_minutes=self.minute-self.scenario_started,
                    reference=copy.deepcopy(self.scenario_reference),note='Changes since activation are observations, not a controlled estimate of fault impact.')

    def snapshot(self):
        grade=self.rom_cu/self.rom_t*100 if self.rom_t>1e-8 else self.last_grade
        hardness=self.rom_hardness/self.rom_t if self.rom_t>1e-8 else self.last_hardness
        ore=sum(t['payload'] for t in self.trucks if t['material']=='ore')
        waste=sum(t['payload'] for t in self.trucks if t['material']=='waste')
        cu=sum(t['cu'] for t in self.trucks if t['material']=='ore')
        recovery=self.recovery(self.last_grade,self.last_hardness)
        trucks=copy.deepcopy(self.trucks)
        for t in trucks:t['stage_progress']=min(1,t['timer']/max(1,t['duration']))
        resources={f:dict(remaining_t=self.remaining[f],initial_t=self.reserve_initial[f],
            state='depleted' if self.remaining[f]<1e-8 else 'available') for f in self.remaining}
        roads={r:dict(capacity_vph_per_lane=self.route_capacity(r),length_km=3.8 if r=='road-main' else 5.2,
            gradient_pct=self.settings['main_grade'] if r=='road-main' else self.settings['north_grade'],
            closed=r=='road-main' and self.road_main_closed,entries=dict(self.road_entries[r]),
            occupancy=sum(t['route']==r and t['state'] in ('loaded_haul','empty_return') for t in trucks),
            queue=sum(t['state'] in ('queue_road_loaded','queue_road_empty') for t in trucks) if r==('road-north' if self.road_main_closed else 'road-main') else 0)
            for r in self.road_next}
        shovels=[]
        for i in range(2):
            active=next((t for t in trucks if t['state']=='loading' and self.shovel(t['face'])==i),None)
            shovels.append(dict(id=f'shovel-{i+1:02}',state='fault' if not self.shovel_online[i] else 'loading' if active else 'available',
                truck=active['id'] if active else None,face=active['face'] if active else None,
                bucket_t=self.settings['bucket_t'],utilization_pct=self.shovel_seconds[i]/max(1,self.minute*60)*100,
                payload_rate=active['load_target']/active['duration']*3600 if active and self.shovel_online[i] else 0))
        grades=[self.face_props[f]['grade'] for f in self.available_faces()]
        feasible=bool(grades) and min(grades)<=self.settings['target_grade']<=max(grades)
        blend=dict(feasible=feasible,min_grade=min(grades) if grades else None,max_grade=max(grades) if grades else None,
            target=self.settings['target_grade'],basis='New ore from currently available faces; existing ROM may temporarily differ')
        return dict(blend_feasibility=blend,resources=resources,roads=roads,shovels=shovels,last_dispatch=copy.deepcopy(self.last_dispatch),
            metrics=dict(energy_kwh=self.energy_kwh,grade_mae_pp=self.grade_error_mass/self.processed if self.processed else None,
                below_target_minutes=self.starved_minutes,truck_wait_minutes=self.wait_seconds/60,
                tailings_t=self.tailings_total,recovered_cu_t=self.recovered_cu),
            reserve_balance_error=sum(self.reserve_initial.values())-sum(self.remaining.values())-self.ore_mined-self.waste_mined,
            processing_balance_error=self.processed-self.concentrate_total-self.tailings_total,
            impact=self.impact(),minute=self.minute,scenario=self.active_scenario,ore_mined=self.ore_mined,waste_mined=self.waste_mined,
            waste_dumped=self.waste_dumped,processed=self.processed,processed_cu=self.processed_cu,feed_rate=self.last_feed,grade=grade,hardness=hardness,
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


def dispatch_experiment(mine,scenario='baseline',minutes=240):
    """Matched starting state, per-truck service streams. No change to operating run."""
    if isinstance(minutes,bool) or not isinstance(minutes,int) or not 30<=minutes<=480:
        raise ValueError('Experiment horizon must be an integer from 30 to 480 minutes')
    runs={};series=[]
    for policy in ('rotation','adaptive'):
        m=copy.deepcopy(mine);m.settings['dispatch']=policy;m.apply_scenario(scenario)
        runs[policy]=m
    initial=dict(processed=mine.processed,concentrate=mine.concentrate_total,
        wait=mine.wait_seconds,energy=mine.energy_kwh,grade=mine.grade_error_mass,starved=mine.starved_minutes)
    for minute in range(1,minutes+1):
        for m in runs.values():m.step(60)
        if minute%10==0:
            series.append(dict(minute=minute,**{k:round(m.processed-initial['processed'],2) for k,m in runs.items()}))
    results={}
    for policy,m in runs.items():
        processed=m.processed-initial['processed'];s=m.snapshot()
        results[policy]=dict(processed_t=processed,concentrate_t=m.concentrate_total-initial['concentrate'],
            grade_mae_pp=(m.grade_error_mass-initial['grade'])/processed if processed else None,
            below_target_minutes=m.starved_minutes-initial['starved'],truck_wait_minutes=(m.wait_seconds-initial['wait'])/60,
            energy_kwh=m.energy_kwh-initial['energy'],final_rom_t=m.rom_t,
            max_balance_error_t=max(abs(s[k]) for k in ('ore_balance_error','copper_balance_error','waste_balance_error','reserve_balance_error','processing_balance_error')))
    delta={k:(results['adaptive'][k]-results['rotation'][k]) if results['adaptive'][k] is not None and results['rotation'][k] is not None else None for k in results['rotation']}
    return dict(scenario=scenario,horizon_minutes=minutes,start_minute=mine.minute,seed=mine.settings['seed'],
        settings=dict(mine.settings),results=results,delta=delta,series=series,
        below_target_definition='Feed below 80% of configured crusher capacity, including outages',
        note='Synthetic controlled comparison. Both policies inherit the same trucks, material, road reservations and seed. Existing assignments finish before policy changes affect new decisions. Positive delta means adaptive minus rotation; lower grade error and waiting are preferable. No guaranteed winner.')
