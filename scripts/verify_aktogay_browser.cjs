// Optional browser verification. Set PLAYWRIGHT_MODULE to an installed Playwright package.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {spawn}=require('child_process');const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..'),evidence=path.join(root,'docs/evidence');fs.mkdirSync(evidence,{recursive:true});
const base=process.env.AKTOGAY_URL||'http://127.0.0.1:8091';
const standalone=process.argv.includes('--standalone');let server;
if(standalone)server=spawn('python3',[path.join(root,'team/aktogay/app.py')],{env:{...process.env,AKTOGAY_MODE:'standalone',WEB_PORT:'8091'},stdio:'ignore'});
const checks=[],errors=[];const check=(label,condition)=>{assert(condition,label);checks.push(label);console.log('PASS',label)};
(async()=>{let browser;try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1600,height:1000},deviceScaleFactor:1});
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 for(let i=0;i<30;i++){try{await page.goto(base);break}catch(e){if(i===29)throw e;await new Promise(r=>setTimeout(r,200));}}
 const state=async()=>{const r=await page.request.get(base+'/api/state');return(await r.json()).snapshot};
 const wait=async predicate=>{for(let i=0;i<60;i++){let s=await state();if(s&&predicate(s))return s;await page.waitForTimeout(250);}throw Error('Snapshot condition timed out')};
 await wait(s=>s.status==='ready');await page.locator('#simulation').waitFor();await page.waitForFunction(()=>!document.querySelector('#simulation').disabled);
 check('WebGL canvas created',await page.locator('#scene canvas').count()===1);
 await page.screenshot({path:path.join(evidence,'ready.png')});
 await page.locator('#simulation').click();await wait(s=>s.status==='running'&&s.minute>0);
 const before=await state();await page.waitForTimeout(1400);const after=await state();check('Clock and truck route positions advance',after.minute>before.minute&&after.trucks.some((t,i)=>t.position!==before.trucks[i].position));
 check('Normal operation has nonzero feed',after.feed_rate>0);
 await page.locator('#simulation').click();await wait(s=>s.status==='paused');const frozen=await state();await page.waitForTimeout(1000);check('Pause holds model time',Math.abs((await state()).minute-frozen.minute)<1e-10);
 await page.locator('#simulation').click();await wait(s=>s.status==='running');
 await page.locator('#speed').selectOption('180');await wait(s=>s.settings.speed===180);
 await page.locator('#whatifMode').click();
 const cases={'power-limit':s=>s.available_mw<=45&&s.feed_rate<=45000/21+.1,'road-closure':s=>s.road_main_closed,'truck-breakdown':s=>s.trucks.some(t=>t.state==='maintenance'),'low-grade':s=>s.face_props['face-east'].grade===.18,'hard-ore':s=>s.face_props['face-north'].hardness===20,'crusher-outage':s=>s.crusher_state==='fault'&&s.feed_rate===0,'shovel-outage':s=>s.shovels.some(x=>x.state==='fault'),'road-congestion':s=>s.roads['road-main'].capacity_vph_per_lane===12};
 for(const[id,predicate]of Object.entries(cases)){
  await page.locator(`[data-scenario="${id}"]`).click();await page.locator('#applyScenario').click();const s=await wait(s=>s.scenario===id&&predicate(s));check('UI scenario '+id,predicate(s));
  if(id==='power-limit')await page.screenshot({path:path.join(evidence,'power-limit.png')});
 }
 await page.locator('#restore').click();await wait(s=>s.scenario==='baseline');check('Restore normal conditions',true);
 await page.locator('#simulation').click();await wait(s=>s.status==='paused');await page.locator('#settingsOpen').click();
 await page.locator('[name="fleet"]').fill('6');await page.locator('[name="power_mw"]').fill('60');await page.getByRole('button',{name:'Apply & reset shift'}).click();
 await wait(s=>s.status==='ready'&&s.settings.fleet===6&&s.available_mw===60);check('Settings apply to backend and reset shift',true);
 await page.locator('#simulation').click();await wait(s=>s.status==='running');await page.waitForTimeout(13500);
 const cycling=await state();check('Fleet completes loading, haul, dump and return cycles',cycling.trucks.some(t=>t.trips>0));
 await page.locator('#forecastScenario').selectOption('power-limit');await page.locator('#forecast').click();const compared=await wait(s=>s.comparison?.scenario==='power-limit');
 check('Paired forecast produces lower processed tonnes under power limit',compared.comparison.alternative.processed_t<compared.comparison.baseline.processed_t);
 await page.getByRole('button',{name:'Inspect PRIMARY CRUSHER'}).click();check('3D asset inspector opens',await page.locator('#inspector').isVisible());await page.locator('#closeInspector').click();
 await page.locator('#simulation').click();await wait(s=>s.status==='paused');await page.waitForTimeout(700);
 await page.locator('#quality').click();await page.waitForTimeout(300);await page.screenshot({path:path.join(evidence,'operations.png')});await page.locator('#quality').click();
 await page.locator('#simulation').click();await wait(s=>s.status==='running');
 const fps=await page.evaluate(()=>new Promise(resolve=>{let start=performance.now(),count=0;function tick(){count++;if(performance.now()-start>1500)resolve(Math.round(count*1000/(performance.now()-start)));else requestAnimationFrame(tick)}requestAnimationFrame(tick)}));
 console.log('MEASURED software-rendered browser fps',fps);await page.locator('#simulation').click();await wait(s=>s.status==='paused');
 await page.locator('#overlay').click();check('Resource overlay toggles',await page.locator('#overlay').innerText()==='Overlay: resources');
 await page.locator('#experimentScenario').selectOption('baseline');await page.locator('#experimentRun').click();
 await wait(s=>s.experiment!==null);await page.locator('#experimentDialog').waitFor({state:'visible'});
 check('Dispatch experiment result visible',await page.locator('#experimentDialog').innerText().then(t=>t.includes('Adaptive')));
 await page.screenshot({path:path.join(evidence,'dispatch-experiment.png')});await page.locator('#experimentClose').click();
 await page.locator('#settingsOpen').click();await page.screenshot({path:path.join(evidence,'settings.png')});await page.locator('#settingsClose').click();
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(500);check('Mobile layout has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(evidence,'mobile.png'),fullPage:true});
 check('No browser console or JavaScript errors',errors.length===0);
 fs.writeFileSync(path.join(evidence,'browser-report.json'),JSON.stringify({mode:standalone?'standalone local model':'integrated',checks,errors,software_browser_fps:fps,full_docker_stack_verified:false,platform_readback_checked:!standalone,measured_at:new Date().toISOString()},null,2));
 }finally{if(browser)await browser.close();if(server)server.kill();}
})().catch(e=>{console.error(e);if(server)server.kill();process.exitCode=1});
