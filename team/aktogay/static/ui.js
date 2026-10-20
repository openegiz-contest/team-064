import {MineScene} from './scene.js';
const $=id=>document.getElementById(id),fmt=(n,d=0)=>Number(n).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
let scene,snapshot=null,transport=null,selected='power-limit',mode='normal',inspected=null,pending=0,busy=false,toastTimer;
const icons=['⊘','⚒','↗','ϟ','Cu','H'];
function toast(message,error=false){$('toast').textContent=message;$('toast').className=error?'error':'';$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,error?8000:4500);}
function message(title,detail){$('sceneMessage').hidden=false;$('sceneMessage').querySelector('strong').textContent=title;$('sceneMessage').querySelector('small').textContent=detail;}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
try{scene=new MineScene($('scene'),$('labels'),id=>{inspected=id;scene?.select(id);inspect();});$('quality').textContent='Quality: '+(scene.software?'software / efficient':'balanced');}catch(e){message('3D graphics unavailable',e.message+' — enable browser hardware acceleration.');console.error(e);}
async function api(path,body){const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{cache:'no-store'});const value=await response.json();if(!response.ok)throw Error(value.error||`HTTP ${response.status}`);return value;}
async function command(path,body){if(busy)return;busy=true;try{const result=await api(path,body);pending=result.sequence||0;toast(result.message||'Request accepted');await poll();return result;}catch(e){toast(e.message,true);}finally{busy=false;}}
function setMode(m){mode=m;$('normalMode').classList.toggle('active',m==='normal');$('whatifMode').classList.toggle('active',m==='whatif');$('scenarioPanel').hidden=m!=='whatif';$('normalPanel').hidden=m!=='normal';}
$('normalMode').onclick=()=>setMode('normal');$('whatifMode').onclick=()=>setMode('whatif');
$('simulation').onclick=()=>command('/api/control',{action:snapshot?.status==='running'?'pause':'start'});
$('reset').onclick=()=>command('/api/reset',{});
$('speed').onchange=e=>command('/api/control',{action:'speed',speed:Number(e.target.value)});
$('applyScenario').onclick=()=>command('/api/scenario',{id:selected});
$('restore').onclick=async()=>{if(await command('/api/scenario',{id:'baseline'}))setMode('normal');};
$('forecast').onclick=async()=>{const button=$('forecast');button.disabled=true;button.textContent='Comparing paired runs…';await command('/api/compare',{id:$('forecastScenario').value});button.disabled=false;button.textContent='↗ Compare next 60 min';};
$('fitView').onclick=()=>scene?.fit();$('topView').onclick=()=>scene?.top();$('quality').onclick=()=>{$('quality').textContent='Quality: '+(scene?.quality()||'unavailable');};
$('closeInspector').onclick=()=>{inspected=null;scene?.select(null);$('inspector').hidden=true;};
$('export').onclick=()=>{if(!snapshot)return toast('No confirmed run to export',true);const report={application:'Aktogay Shift Operations 2.0',exported_at:new Date().toISOString(),data:'Synthetic decision-support model; not operator telemetry',transport,snapshot};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));a.download=`aktogay-shift-${snapshot.run_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
const fields=[['fleet','Active trucks','vehicles',2,8,1],['crusher_tph','Crusher capacity','t/h',500,4500,100],['power_mw','Power supply','MW',10,90,1],['load_minutes','Loading duration','minutes per truck',3,12,.5],['haul_minutes','Main loaded haul','minutes',5,20,.5],['target_grade','Blend target','% Cu',.15,.8,.01],['f1_grade','F1 copper grade','% Cu',.1,1,.01],['f2_grade','F2 copper grade','% Cu',.1,1,.01],['f3_grade','F3 copper grade','% Cu',.1,1,.01],['hardness','Base ore hardness','kWh/t; face offsets documented',8,24,.1],['seed','Random seed','repeatable experiment',0,999999,1]];
$('settingsFields').innerHTML=fields.map(([name,label,unit,min,max,step])=>`<label class="field">${label}<input name="${name}" type="number" min="${min}" max="${max}" step="${step}" required><small>${unit} · ${min}–${max}</small></label>`).join('');
let defaults={};function fill(settings){for(const[name]of fields)$('settingsForm').elements[name].value=settings[name];$('settingsForm').elements.dispatch.value=settings.dispatch;}
$('settingsOpen').onclick=()=>{fill(snapshot?.settings||defaults);$('settingsDialog').showModal();};$('settingsClose').onclick=()=>$('settingsDialog').close();$('defaults').onclick=()=>fill(defaults);
$('settingsForm').onsubmit=async e=>{e.preventDefault();if(snapshot?.status==='running')return toast('Pause Simulation before changing model settings.',true);const values={};for(const[name]of fields)values[name]=Number($('settingsForm').elements[name].value);values.dispatch=$('settingsForm').elements.dispatch.value;if(await command('/api/settings',values))$('settingsDialog').close();};
function inspect(){if(!inspected||!snapshot)return;$('inspector').hidden=false;let s=snapshot,title,values;
 const t=s.trucks.find(t=>t.id===inspected);
 if(t){title=t.label;values={State:t.state.replaceAll('_',' '),Payload:fmt(t.payload,1)+' t',Assignment:t.face.replace('face-',''),Route:t.route==='road-north'?'North alternate':'Main haul',Trips:t.trips,Speed:s.status==='running'?fmt(t.speed)+' km/h':'Held'};}
 else if(inspected==='rom-01'){title='ROM buffer';values={Inventory:fmt(s.rom_t)+' t',Capacity:'24,000 t',Grade:fmt(s.grade,3)+'% Cu',Hardness:fmt(s.hardness,2)+' kWh/t'};}
 else if(inspected==='crusher-01'){title='CR-01 · Primary crusher';values={State:s.crusher_state,Throughput:fmt(s.feed_rate)+' t/h',Processed:fmt(s.processed)+' t',Queue:s.queue+' trucks'};}
 else if(inspected==='concentrator-01'){title='Sulphide concentrator';values={Feed:fmt(s.feed_rate)+' t/h',Recovery:fmt(s.recovery,1)+'%',Concentrate:fmt(s.concentrate_tph,1)+' t/h',Basis:'25 Mt/year design'};}
 else if(inspected==='substation-01'){title='Plant substation';values={Supply:fmt(s.available_mw)+' MW',Demand:fmt(s.power_draw,1)+' MW','Energy intensity':'21 kWh/t'};}
 else if(inspected==='pit'){title='Sulphide pit phase';values={Faces:'3 ore + 1 waste',Fleet:s.settings.fleet+' trucks',Shovels:'2 shared resources',Geometry:'Schematic'};}
 else{title=inspected.replace('shovel-','SH-');values={Status:s.status==='running'?'In service':'Held',Loading:fmt(s.settings.load_minutes,1)+' min',Dispatch:s.settings.dispatch};}
 $('assetName').textContent=title;$('assetData').innerHTML='<dl>'+Object.entries(values).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')+'</dl>';
}
function render(data){transport=data.transport;const s=data.snapshot;const local=transport.mode==='standalone',fresh=transport.fresh;
 $('connection').textContent=local?'LOCAL MODEL · PLATFORM OFF':fresh?'DITTO CONFIRMED':s?'TELEMETRY STALE':'WAITING FOR DITTO';$('connection').className='connection '+(local||!fresh?'warn':'good');
 $('source').textContent=local?'Local development mode · not a contest Stand':'Source: Eclipse Ditto ← MQTT ← simulation';
 $('freshness').textContent=transport.age_s==null?'No confirmed snapshot':`Snapshot ${transport.age_s.toFixed(1)}s old · ${s?.run_id||''}`;
 if(!s){message('Waiting for platform confirmation',transport.error||'Connecting to Eclipse Ditto. No placeholder values are shown as live data.');return;}
 snapshot=s;scene?.update(s,fresh);if(pending&&s.sequence>=pending)pending=0;
 if(!fresh)message('Telemetry is stale',transport.error||'The scene is held at its last confirmed position. Check MQTT and Ditto.');
 else if(pending)message('Confirming your command','Waiting for the updated snapshot to return through the platform.');
 else if(s.status==='ready')message('Your shift is ready','Press Start Simulation to set the haulage and processing chain in motion.');
 else if(s.status==='paused')message('Simulation paused','Equipment and material are held. Resume to continue this shift.');
 else if(s.status==='error')message('Simulation stopped after an error','Inspect the service logs before restarting.');
 else $('sceneMessage').hidden=true;
 const seconds=Math.floor(s.minute*60);$('simClock').textContent=[Math.floor(seconds/3600),Math.floor(seconds/60)%60,seconds%60].map(v=>String(v).padStart(2,'0')).join(':');
 $('statusBadge').textContent=s.status.toUpperCase();$('statusBadge').className='badge '+(s.status==='running'?'running':'amber');
 $('simulation').textContent=s.status==='running'?'Ⅱ Pause Simulation':s.status==='paused'?'▶ Resume Simulation':'▶ Start Simulation';$('simulation').disabled=!fresh||pending>0;
 $('applyScenario').disabled=s.status!=='running'||!fresh||pending>0;
 $('controlHint').textContent=s.scenario==='baseline'?'Normal operation · '+s.active_fleet+' available trucks · '+s.settings.dispatch+' dispatch.':'ACTIVE: '+s.scenario.replaceAll('-',' ')+' · inspect the chain and dispatch log.';
 $('speed').value=String(s.settings.speed);
 $('feed').textContent=fmt(s.feed_rate);$('grade').textContent=fmt(s.grade,3);$('rom').textContent=fmt(s.rom_t);$('power').textContent=fmt(s.power_draw,1);
 $('feedHint').textContent=s.status==='ready'?'Ready · awaiting start':`${fmt(s.processed)} t processed this shift`;
 $('gradeHint').textContent=`Target ${fmt(s.settings.target_grade,2)}% · hardness ${fmt(s.hardness,1)}`;
 $('powerHint').textContent=`Supply limit ${fmt(s.available_mw)} MW`;$('romBar').style.width=Math.min(100,s.rom_pct)+'%';
 $('fleetBadge').textContent=`${s.active_fleet} / ${s.settings.fleet} trucks`;$('haulCount').textContent=s.trucks.filter(t=>t.state==='loaded_haul').length+' hauling';
 $('haulState').textContent=s.road_main_closed?'North route · committed main trips clearing':'Main road open';$('crusherState').textContent=s.crusher_state==='fault'?'Offline · ROM buffering incoming ore':'Available · '+fmt(s.rom_pct)+'% ROM fill';$('queueCount').textContent=s.queue+' queued';
 $('recovery').textContent=fmt(s.recovery,1)+'%';$('recoveryState').textContent=fmt(s.concentrate_tph,1)+' t/h concentrate estimate';
 const balance=Math.max(Math.abs(s.ore_balance_error),Math.abs(s.waste_balance_error),Math.abs(s.copper_balance_error));$('balance').textContent=balance<.01?'Balanced · < 0.01 t':'ERROR · '+fmt(balance,2)+' t';
 $('events').innerHTML=s.events.slice(0,14).map(e=>`<li><time>SIM ${fmt(e.minute,1)} MIN</time>${esc(e.text)}</li>`).join('');
 const history=s.history||[];$('chartSummary').textContent=history.length+' confirmed samples';if(history.length){const min=history[0].minute,max=Math.max(min+1,history.at(-1).minute),cap=Math.max(3500,s.settings.crusher_tph*1.1);const points=history.map(p=>[(p.minute-min)/(max-min)*1000,90-Math.min(cap,p.feed_rate)/cap*80]);const line='M'+points.map(p=>p.map(v=>v.toFixed(2)).join(',')).join('L');$('chartLine').setAttribute('d',line);$('chartArea').setAttribute('d',line+`L${points.at(-1)[0]},100L0,100Z`);$('chartStart').textContent=fmt(min)+' min';$('chartEnd').textContent=fmt(history.at(-1).minute)+' min';}else{$('chartLine').setAttribute('d','');$('chartArea').setAttribute('d','');$('chartStart').textContent='0 min';$('chartEnd').textContent='Start Simulation to collect samples';}
 const c=s.comparison;$('forecastResult').hidden=!c;if(c){const delta=c.alternative.processed_t-c.baseline.processed_t;$('forecastResult').innerHTML=`<div class="forecast-metrics"><div><span>Normal · processed</span><b>${fmt(c.baseline.processed_t)} t</b></div><div><span>${esc(c.scenario)} · processed</span><b>${fmt(c.alternative.processed_t)} t</b></div><div><span>Change over 60 min</span><b class="delta">${delta>=0?'+':''}${fmt(delta)} t</b></div><div><span>Alternative ROM inventory</span><b>${fmt(c.alternative.rom_t)} t</b></div></div><p class="muted">Paired forecast from sim minute ${fmt(c.start_minute,1)}. Same initial material and seed. Synthetic model; no operational prediction.</p>`;}
 inspect();
}
let polling=false;async function poll(){if(polling)return;polling=true;try{render(await api('/api/state'));}catch(e){if(transport)transport.fresh=false;scene?.update(snapshot,false);$('connection').textContent='CONNECTION LOST';$('connection').className='connection warn';$('simulation').disabled=true;$('applyScenario').disabled=true;message('Connection lost',e.message+'. The last confirmed scene is held; retrying automatically.');}finally{polling=false;}}
async function init(){try{const data=await api('/api/scenarios');defaults=data.defaults;$('scenarios').innerHTML=data.scenarios.map((s,i)=>`<button class="scenario-card ${s.id===selected?'selected':''}" data-scenario="${s.id}" title="${esc(s.description)}"><span>${icons[i]}</span><div><strong>${esc(s.name)}</strong><small>${esc(s.short)}</small></div></button>`).join('');document.querySelectorAll('[data-scenario]').forEach(b=>b.onclick=()=>{selected=b.dataset.scenario;document.querySelectorAll('[data-scenario]').forEach(x=>x.classList.toggle('selected',x===b));$('forecastScenario').value=selected;});$('forecastScenario').innerHTML=data.scenarios.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('');$('forecastScenario').value=selected;fill(defaults);}catch(e){toast('Cannot load scenario catalogue: '+e.message,true);}await poll();setInterval(poll,800);}
init();
