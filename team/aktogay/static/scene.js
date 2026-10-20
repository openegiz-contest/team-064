import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {mergeGeometries} from './vendor/BufferGeometryUtils.js';

// Original procedural mine and articulated equipment; units are schematic metres.
export class MineScene {
 constructor(host,labels,onSelect){
  this.host=host;this.labelHost=labels;this.onSelect=onSelect;this.state=null;this.previous=null;this.received=0;this.labels=[];this.pickables=[];this.trucks=[];this.excavators=[];this.beltPieces=[];this.high=false;
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#182a38');this.scene.fog=new THREE.Fog('#182a38',280,620);
  this.camera=new THREE.PerspectiveCamera(38,1,.5,1300);
  this.renderer=new THREE.WebGLRenderer({antialias:false,alpha:false,powerPreference:'high-performance'});
  const gl=this.renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');this.software=!!ext&&/swiftshader|llvmpipe|software/i.test(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL));this.renderer.setPixelRatio(this.software?.65:Math.min(devicePixelRatio,1.25));this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.autoUpdate=false;this.renderer.shadowMap.needsUpdate=true;this.renderer.shadowMap.type=THREE.BasicShadowMap;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.35;
  host.appendChild(this.renderer.domElement);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.075;this.controls.minDistance=45;this.controls.maxDistance=390;this.controls.maxPolarAngle=Math.PI*.47;this.controls.target.set(0,-3,0);this.fit();
  this.scene.add(new THREE.HemisphereLight(0xc8e3f2,0x8d7053,2.3));
  const sun=new THREE.DirectionalLight(0xffe4bc,3.5);sun.position.set(-65,130,70);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-150;sun.shadow.camera.right=150;sun.shadow.camera.top=130;sun.shadow.camera.bottom=-130;sun.shadow.camera.near=1;sun.shadow.camera.far=360;sun.shadow.normalBias=.15;sun.shadow.bias=-.00015;this.scene.add(sun);this.sun=sun;
  const rim=new THREE.DirectionalLight(0xa6d6ff,1);rim.position.set(100,60,-90);this.scene.add(rim);
  this.mat={sand:this.material('#ad936e'),bench:this.material('#b8a27e'),rock:this.material('#82735f'),road:this.material('#796e5a'),dark:this.material('#23343c'),steel:this.material('#7d999e',.55,.45),yellow:this.material('#e8b447',.2,.55),light:this.material('#d4d5bc',.25,.6),rubber:this.material('#19232a'),glass:this.material('#284958',.65,.2),belt:this.material('#2e3b3e'),rail:this.material('#e0bf67',.3,.4),ore:this.material('#817355')};
  const tex=new THREE.TextureLoader().load('/static/assets/Ground037_1K-JPG_Color.jpg');tex.colorSpace=THREE.SRGBColorSpace;tex.wrapS=tex.wrapT=THREE.RepeatWrapping;tex.repeat.set(.065,.065);tex.anisotropy=4;this.mat.sand.map=tex;
  this.commonRamp=this.rampPoints();this.buildTerrain();this.buildRoads();this.buildPlant();this.buildDetails();
  for(let i=0;i<8;i++){const truck=this.makeTruck(i);this.trucks.push(truck);this.scene.add(truck.group);}
  this.addExcavator([-52,-22,1],0);this.addExcavator([-26,-22,-12],1);
  this.addLabel('PIT PHASE 01',[-45,-3,-42],'pit');this.addLabel('ROM BUFFER',[40,11,27],'rom-01');this.addLabel('PRIMARY CRUSHER',[59,17,4],'crusher-01');this.addLabel('CONCENTRATOR',[73,20,-29],'concentrator-01');this.addLabel('SUBSTATION',[38,8,-42],'substation-01');
  for(const o of [...this.trucks.map(t=>t.group),...this.excavators.map(e=>e.g),this.pile,...this.beltPieces.map(p=>p.mesh)])o.traverse(m=>{if(m.isMesh)m.castShadow=false;});
  this.mergeStatic();
  this.selectionRing=new THREE.Mesh(new THREE.TorusGeometry(3.7,.12,8,60),new THREE.MeshBasicMaterial({color:0x78efd3,transparent:true,opacity:.85,depthTest:false}));this.selectionRing.rotation.x=-Math.PI/2;this.selectionRing.visible=false;this.scene.add(this.selectionRing);
  this.ray=new THREE.Raycaster();this.pointer=new THREE.Vector2();let down;
  host.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY]});host.addEventListener('pointerup',e=>{if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;const r=host.getBoundingClientRect();this.pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.ray.setFromCamera(this.pointer,this.camera);let hit=this.ray.intersectObjects(this.pickables,true)[0];if(hit){let o=hit.object;while(o&&!o.userData.asset)o=o.parent;if(o)this.onSelect(o.userData.asset);}});
  new ResizeObserver(()=>this.resize()).observe(host);this.resize();this.animate();
 }
 mergeParts(group,exclude=[]){
  this.scene.updateMatrixWorld(true);group.updateMatrixWorld(true);const inverse=group.matrixWorld.clone().invert(),batches=new Map(),remove=[];
  group.traverse(o=>{if(!o.isMesh)return;let p=o;while(p&&p!==group){if(exclude.includes(p))return;p=p.parent;}const key=o.material.uuid;if(!batches.has(key))batches.set(key,{material:o.material,geometries:[]});let g=o.geometry.index?o.geometry.toNonIndexed():o.geometry.clone();g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inverse,o.matrixWorld));batches.get(key).geometries.push(g);remove.push(o);});
  for(const o of remove)o.removeFromParent();for(const batch of batches.values()){this.mesh(mergeGeometries(batch.geometries,false),batch.material,group);for(const g of batch.geometries)g.dispose();}
 }
 mergeStatic(){
  // Reduce draw calls for the CPU-rendered judge browser; movable/selected assets stay separate.
  this.scene.updateMatrixWorld(true);
  const dynamic=new Set([...this.trucks.map(t=>t.group),...this.excavators.map(e=>e.g),this.pile,this.crusherLamp,this.subLamp,...this.beltPieces.map(p=>p.mesh)]);
  const batches=new Map(),remove=[];
  this.scene.traverse(o=>{if(!o.isMesh||Array.isArray(o.material))return;let p=o,asset='';while(p){if(dynamic.has(p))return;if(p.userData.asset)asset=p.userData.asset;p=p.parent;}
   const key=o.material.uuid+'|'+asset+'|'+Object.keys(o.geometry.attributes).sort().join(',');
   if(!batches.has(key))batches.set(key,{material:o.material,asset,geometries:[]});
   let g=o.geometry.index?o.geometry.toNonIndexed():o.geometry.clone();g.applyMatrix4(o.matrixWorld);batches.get(key).geometries.push(g);remove.push(o);
  });
  for(const o of remove)o.removeFromParent();
  this.pickables=[...this.trucks.map(t=>t.group),...this.excavators.map(e=>e.g),this.pile];
  for(const batch of batches.values()){const geo=mergeGeometries(batch.geometries,false);if(!geo)throw Error('Static geometry merge failed');const mesh=this.mesh(geo,batch.material);if(batch.asset){mesh.userData.asset=batch.asset;this.pickables.push(mesh);}for(const g of batch.geometries)g.dispose();}
 }
 material(color,metalness=0,roughness=.92){return this.software?new THREE.MeshLambertMaterial({color}):new THREE.MeshStandardMaterial({color,metalness,roughness});}
 mesh(geometry,material,parent=this.scene){const o=new THREE.Mesh(geometry,material);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;}
 box(w,h,d,x,y,z,mat,parent=this.scene){const o=this.mesh(new THREE.BoxGeometry(w,h,d),mat,parent);o.position.set(x,y,z);return o;}
 cyl(r1,r2,h,x,y,z,mat,parent=this.scene,n=16){const o=this.mesh(new THREE.CylinderGeometry(r1,r2,h,n),mat,parent);o.position.set(x,y,z);return o;}
 beam(a,b,w,mat,parent=this.scene){a=new THREE.Vector3(...a);b=new THREE.Vector3(...b);let o=this.box(w,a.distanceTo(b),w,0,0,0,mat,parent);o.position.copy(a.clone().add(b).multiplyScalar(.5));o.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),b.sub(a).normalize());return o;}
 fit(){this.camera.position.set(167,157,198);this.controls.target.set(-2,-5,0);this.controls.update();}
 top(){this.camera.position.set(0,235,8);this.controls.target.set(0,-4,0);this.controls.update();}
 quality(){this.high=!this.high;this.renderer.setPixelRatio(Math.min(devicePixelRatio,this.high?1.75:(this.software?.65:1.25)));return this.high?'high':'balanced';}
 resize(){const r=this.host.getBoundingClientRect();this.renderer.setSize(r.width,r.height);this.camera.aspect=r.width/r.height;this.camera.updateProjectionMatrix();}
 contour(r,a){let noise=1+.045*Math.sin(3*a)+.025*Math.cos(7*a);return[-37+51*r*Math.cos(a)*noise,45*r*Math.sin(a)*noise];}
 rampPoints(){const points=[];for(let i=0;i<=100;i++){const t=i/100,a=.6+t*Math.PI*1.83,r=.28+t*.69;let[x,z]=this.contour(r,a);points.push([x,-23+24*t,z]);}points.push([18,1,3],[28,1,10]);return points;}
 buildTerrain(){
  // A continuous cut-and-fill surface, graded around the ramp. No road passes through a bench wall.
  const W=204,D=130,nx=170,nz=110,positions=[],uv=[],colors=[],indices=[];
  for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++){
   const x=-102+W*i/nx,z=-65+D*j/nz,a=Math.atan2(z/45,(x+37)/51),noise=1+.045*Math.sin(3*a)+.025*Math.cos(7*a),r=Math.hypot((x+37)/51,z/45)/noise;
   let y=r>=1?0:r>=.84?-5:r>=.67?-10:r>=.50?-15:r>=.32?-20:-24;
   let distance=1e6,roadY=y;
   for(const p of this.commonRamp){const d=Math.hypot(x-p[0],z-p[2]);if(d<distance){distance=d;roadY=p[1]-.24;}}
   if(distance<5.8){let blend=THREE.MathUtils.smoothstep(distance,3.6,5.8);y=THREE.MathUtils.lerp(roadY,y,blend);}
   positions.push(x,y,z);uv.push(x,z);let tone=r>1?.95:.89+(Math.floor((y+25)/5)%2)*.08;colors.push(tone,tone*.98,tone*.92);
  }
  for(let j=0;j<nz;j++)for(let i=0;i<nx;i++){const a=j*(nx+1)+i,b=a+1,c=a+nx+1,d=c+1;indices.push(a,c,b,b,c,d);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.setIndex(indices);g.computeVertexNormals();
  const ground=this.mat.sand.clone();ground.vertexColors=true;ground.onBeforeCompile=shader=>{shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>','#include <map_fragment>\n float rockLuma=dot(diffuseColor.rgb,vec3(0.299,0.587,0.114));diffuseColor.rgb=mix(diffuseColor.rgb,vec3(rockLuma),0.82)*vec3(1.14,1.02,0.83);');};this.mesh(g,ground);
  for(const[y,h,color]of[[-4,8,'#9e8765'],[-12,8,'#8c7658'],[-20,8,'#766449'],[-27,6,'#5f5543']]){
   const m=this.material(color);this.box(204,h,.25,0,y,65,m);this.box(204,h,.25,0,y,-65,m);this.box(.25,h,130,-102,y,0,m);this.box(.25,h,130,102,y,0,m);
  }
  const floor=this.mesh(new THREE.PlaneGeometry(1800,1800),this.material('#192e3c'));floor.rotation.x=-Math.PI/2;floor.position.y=-30.5;floor.castShadow=false;
  const grid=new THREE.GridHelper(650,26,0x314956,0x233c4b);grid.position.y=-30.4;grid.material.transparent=true;grid.material.opacity=.4;this.scene.add(grid);
 }
 ribbon(points,width,mat,depth=0){
  const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));let vertices=[],uv=[],N=200;
  for(let i=0;i<N;i++){
   const corners=[];
   for(const t of [i/N,(i+1)/N]){const p=curve.getPoint(t),dir=curve.getTangent(t),side=new THREE.Vector3(-dir.z,0,dir.x).normalize().multiplyScalar(width/2);corners.push(p.clone().add(side),p.clone().sub(side));}
   for(const k of [0,1,2,1,3,2]){vertices.push(...corners[k].toArray());uv.push(k%2,i/N*10);}
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.computeVertexNormals();mat=mat.clone();mat.side=THREE.DoubleSide;this.mesh(g,mat);
  if(depth)for(let i=0;i<points.length-1;i++)this.beam([points[i][0],points[i][1]-depth/2,points[i][2]],[points[i+1][0],points[i+1][1]-depth/2,points[i+1][2]],width,this.mat.rock);
  return curve;
 }
 buildRoads(){
  this.faces={'face-west':[-46,-23,3],'face-east':[-29,-23,-8],'face-north':[-44,-23,-13],'face-waste':[-37,-23,7]};
  const ramp=this.commonRamp;
  this.ribbon(ramp,6.2,this.mat.road);
  // Low berms outline the ramp and visually connect the benches.
  this.roadCurve=new THREE.CatmullRomCurve3(ramp.map(p=>new THREE.Vector3(...p)));
  for(let i=0;i<100;i++){const t=i/100,p=this.roadCurve.getPoint(t),d=this.roadCurve.getTangent(t),n=new THREE.Vector3(-d.z,0,d.x).normalize();for(const side of [-1,1]){let v=p.clone().addScaledVector(n,side*3);this.box(1.1,.45,.7,v.x,v.y+.15,v.z,this.mat.rock).rotation.y=-Math.atan2(d.z,d.x);}}
  this.mainEnd=[[28,1,10],[35,1,15],[44,1,16],[49,1,16]];
  this.northEnd=[[28,1,10],[24,1,-5],[29,1,-15],[42,1,-16],[49,1,-6],[49,1,16]];
  this.ribbon(this.mainEnd,5,this.mat.road);this.ribbon(this.northEnd,4.5,this.mat.road);
  this.wasteEnd=[[28,1,10],[20,1,25],[17,1,43],[23,1,49]];this.ribbon(this.wasteEnd,4.5,this.mat.road);
  this.paths={};
  for(const[face,start]of Object.entries(this.faces)){
   this.ribbon([start,ramp[0]],4.2,this.mat.road);
   for(const route of ['road-main','road-north'])for(const material of ['ore','waste']){
    let end=material==='waste'?this.wasteEnd:(route==='road-north'?this.northEnd:this.mainEnd);
    this.paths[face+route+material]=new THREE.CatmullRomCurve3([start,...ramp,...end.slice(1)].map(p=>new THREE.Vector3(...p)));
   }
  }
  this.closure=new THREE.Group();this.closure.position.set(32,1.1,12);this.scene.add(this.closure);
  for(let i=0;i<5;i++){const b=this.box(.65,1,.45,(i-2)*.85,.5,0,i%2?this.mat.light:this.material('#d16d46'),this.closure);}
  this.closure.visible=false;
 }
 makeTruck(i){
  const g=new THREE.Group();g.userData.asset='truck-'+String(i+1).padStart(2,'0');this.pickables.push(g);
  this.box(4,.6,2.2,0,1,0,this.mat.dark,g);this.box(1.2,1.4,2.2,1.2,1.8,0,this.mat.yellow,g);
  this.box(.95,1.05,1.02,1.28,2.85,-.48,this.mat.light,g);this.box(.8,.67,1.07,1.35,2.95,-.48,this.mat.glass,g);
  this.box(.14,.18,2.4,2.06,1.2,0,this.mat.steel,g);
  const wheels=[];
  for(const x of [-1.25,1.3])for(const z of [-1.25,1.25]){
   let w=this.cyl(.73,.73,.48,x,.77,z,this.mat.rubber,g,18);w.rotation.x=Math.PI/2;wheels.push(w);
   let hub=this.cyl(.32,.32,.5,x,.77,z,this.mat.steel,g,12);hub.rotation.x=Math.PI/2;
  }
  const bed=new THREE.Group();bed.position.set(-1.65,1.65,0);g.add(bed);
  this.box(3.05,.18,2.5,1.3,0,0,this.mat.yellow,bed);
  this.box(3.05,1.0,.14,1.3,.43,-1.2,this.mat.yellow,bed);this.box(3.05,1.0,.14,1.3,.43,1.2,this.mat.yellow,bed);
  this.box(.18,.85,2.5,-.15,.42,0,this.mat.yellow,bed);this.box(.2,.9,2.5,2.75,.45,0,this.mat.yellow,bed);
  for(const x of [.25,1.25,2.2])for(const z of [-1.29,1.29])this.box(.13,.82,.08,x,.42,z,this.mat.rail,bed);
  const ore=this.mesh(new THREE.SphereGeometry(1,12,6),this.mat.ore,bed);ore.position.set(1.3,.32,0);ore.scale.set(1.4,.45,1.07);
  for(const z of [-.85,.85]){let l=this.box(.08,.18,.34,2.1,1.65,z,this.material('#f4e8b5',0,.3),g);l.material.emissive.set('#bea46a');l.material.emissiveIntensity=.4;}
  this.beam([.75,3.1,.85],[.75,3.8,.85],.04,this.mat.steel,g);const beacon=this.cyl(.10,.10,.16,.75,3.82,.85,this.material('#eb914c'),g);
  const dustG=new THREE.BufferGeometry(),positions=new Float32Array(9*3);for(let k=0;k<9;k++){positions[k*3]=-2.4-k*.2;positions[k*3+1]=.4+(k%3)*.18;positions[k*3+2]=((k%4)-1.5)*.5;}dustG.setAttribute('position',new THREE.BufferAttribute(positions,3));const dust=new THREE.Points(dustG,new THREE.PointsMaterial({color:0xcbb38d,size:.85,transparent:true,opacity:.25,depthWrite:false}));g.add(dust);
  this.mergeParts(bed,[ore]);this.mergeParts(g,[bed,beacon]);const contact=this.mesh(new THREE.CircleGeometry(2.1,20),new THREE.MeshBasicMaterial({color:0x29271f,transparent:true,opacity:.22,depthWrite:false}),g);contact.rotation.x=-Math.PI/2;contact.position.y=.08;contact.scale.set(1.15,.65,1);contact.castShadow=false;
  g.scale.setScalar(1.45);return {group:g,bed,ore,wheels:[],dust,beacon};
 }
 addExcavator(pos,index){
  const g=new THREE.Group();g.position.set(...pos);g.rotation.y=index?-.6:.5;g.userData.asset='shovel-'+String(index+1).padStart(2,'0');this.pickables.push(g);this.scene.add(g);
  for(const z of [-1.35,1.35]){this.box(4,.85,.8,0,.5,z,this.mat.dark,g);for(let x=-1.5;x<=1.5;x+=.6){let c=this.cyl(.39,.39,.85,x,.5,z,this.mat.steel,g,12);c.rotation.x=Math.PI/2;}}
  this.cyl(1.4,1.4,.6,0,1.2,0,this.mat.steel,g);const turret=new THREE.Group();g.add(turret);turret.position.y=1.45;
  this.box(3.6,1.35,2.5,-.25,.6,0,this.mat.yellow,turret);this.box(1.4,1.4,1.2,.9,1.6,-.5,this.mat.light,turret);this.box(1.25,.95,1.22,.95,1.8,-.5,this.mat.glass,turret);
  for(let x=-1.6;x<-.3;x+=.22)this.box(.08,.03,1.6,x,1.3,0,this.mat.dark,turret);
  const arm=new THREE.Group();arm.position.set(1.3,1,.5);turret.add(arm);this.beam([0,0,0],[3.2,4.5,0],.55,this.mat.yellow,arm);this.beam([.1,.3,.35],[2.7,3.8,.35],.15,this.mat.steel,arm);
  this.beam([3.2,4.5,0],[5.1,1.6,0],.4,this.mat.yellow,arm);this.beam([3.35,4.35,.25],[4.8,2.1,.25],.14,this.mat.steel,arm);
  this.box(1.4,.7,1.4,5,1.3,0,this.mat.dark,arm);for(let z=-.55;z<=.6;z+=.28)this.box(.6,.12,.12,5.6,1.1,z,this.mat.steel,arm);
  this.mergeParts(arm);this.mergeParts(turret,[arm]);this.mergeParts(g,[turret]);g.scale.setScalar(1.85);this.excavators.push({g,turret,arm,index});
 }
 conveyor(a,b,width=2.1){
  const start=new THREE.Vector3(...a),end=new THREE.Vector3(...b),len=start.distanceTo(end);const mid=start.clone().add(end).multiplyScalar(.5);
  const group=new THREE.Group();group.position.copy(mid);group.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),end.clone().sub(start).normalize());
  // Belt built directly along a 3D line; metal truss and edge rails.
  this.beam(a,b,width,this.mat.dark);
  for(const off of [-width*.58,width*.58]){this.beam([a[0]+off,a[1]+.6,a[2]],[b[0]+off,b[1]+.6,b[2]],.14,this.mat.rail);}
  for(let t=.1;t<1;t+=.17){let p=start.clone().lerp(end,t);this.beam([p.x,0,p.z],[p.x,p.y-.6,p.z],.45,this.mat.steel);this.beam([p.x-1.8,0,p.z],[p.x,p.y-.6,p.z],.22,this.mat.steel);}
  for(let i=0;i<15;i++){const rock=this.mesh(new THREE.DodecahedronGeometry(.35,0),this.mat.ore);this.beltPieces.push({mesh:rock,a:start,b:end,offset:i/15});}
 }
 buildPlant(){
  // Concrete operating apron, with lane markings and curb.
  this.box(69,.35,101,65,.2,-4,this.material('#657071'));
  for(let z=-48;z<44;z+=6)this.box(.12,.03,2,96,.4,z,this.mat.light);
  // ROM stockpile, scaled from the simulation inventory.
  const pile=this.mesh(new THREE.ConeGeometry(9,8,48),this.material('#a8956e'));pile.position.set(40,4.6,29);this.pile=pile;pile.userData.asset='rom-01';this.pickables.push(pile);
  this.box(24,.7,24,40,.35,29,this.mat.rock);this.box(.5,3,22,28,1.5,29,this.mat.light);this.box(24,3,.5,40,1.5,41,this.mat.light);
  const waste=this.mesh(new THREE.ConeGeometry(9,5,12),this.mat.rock);waste.position.set(22,2.8,51);
  // Primary crusher with hopper, frame, platform and service stairs.
  const crusher=new THREE.Group();crusher.userData.asset='crusher-01';this.pickables.push(crusher);this.scene.add(crusher);crusher.position.set(59,0,5);
  for(const x of [-4,4])for(const z of [-3,3])this.box(.6,10,.6,x,5,z,this.mat.steel,crusher);
  this.box(10,.65,9,0,8.8,0,this.mat.steel,crusher);this.box(6,6,6,0,4,0,this.mat.light,crusher);
  this.cyl(4.3,1.5,4,0,10.6,0,this.mat.yellow,crusher,4).rotation.y=Math.PI/4;
  this.cyl(3.6,3.6,.1,0,12.63,0,this.mat.dark,crusher,4).rotation.y=Math.PI/4;
  for(const z of [-4.3,4.3]){this.beam([-5,10,z],[5,10,z],.12,this.mat.rail,crusher);for(let x=-5;x<=5;x+=2)this.beam([x,8.8,z],[x,10,z],.10,this.mat.rail,crusher);}
  for(let i=0;i<14;i++)this.box(2,.2,.65,6,1+i*.55,6-i*.5,this.mat.steel,crusher);
  this.crusherLamp=this.cyl(.45,.45,.2,3,13.2,2,this.material('#6bd4bd'),crusher);
  this.conveyor([41,5,28],[58,12,5]);this.conveyor([61,4,0],[73,9,-20]);
  // Concentrator building: corrugated shell, steel ribs, glazed clerestory.
  const plant=new THREE.Group();plant.position.set(74,0,-30);plant.userData.asset='concentrator-01';this.pickables.push(plant);this.scene.add(plant);
  this.box(24,12,20,0,6,0,this.mat.light,plant);
  const roof=this.box(25,.7,21,0,12.3,0,this.material('#49717a',.4,.6),plant);roof.rotation.z=.04;
  for(let x=-11.5;x<12;x+=1.15){this.box(.13,11,.1,x,6,10.08,this.mat.steel,plant);this.box(.13,11,.1,x,6,-10.08,this.mat.steel,plant);}
  for(let x=-10;x<12;x+=4)this.box(2.8,1.4,.12,x,10.3,10.15,this.mat.glass,plant);
  this.box(6,5,.2,5,2.5,10.2,this.mat.dark,plant);
  for(const x of [-6,3]){this.cyl(1.5,1.5,3,x,14,0,this.mat.steel,plant);this.cyl(1.8,1.8,.2,x,15.5,0,this.mat.dark,plant);}
  for(const x of [52,61]){this.cyl(3,3,6,x,3,-26,this.mat.steel);this.cyl(3.15,3.15,.3,x,6.2,-26,this.mat.light);}
  // Thickener and processing tanks connected by visible pipework.
  this.cyl(8.5,8.5,2.5,77,1.6,-52,this.mat.light,undefined,40);this.cyl(8,8,.1,77,2.9,-52,this.material('#385b61',.35,.3),undefined,40);this.beam([68,3.4,-52],[86,3.4,-52],.35,this.mat.steel);
  this.beam([61,4,-26],[65,4,-26],.7,this.mat.steel);this.beam([77,3,-43],[77,3,-48],.6,this.mat.steel);
  // Electrical switchyard: transformer banks, insulators and gantry.
  const sub=new THREE.Group();sub.position.set(35,.3,-39);sub.userData.asset='substation-01';this.scene.add(sub);this.pickables.push(sub);
  this.box(19,.2,18,0,0,0,this.mat.rock,sub);
  for(const x of [-5,1,7]){this.box(3,3,4,x,1.7,0,this.mat.steel,sub);for(let z=-1.4;z<2;z+=.7)this.box(3.7,2.5,.17,x,1.5,z,this.mat.dark,sub);for(const z of [-1,1]){this.cyl(.2,.2,1.5,x,3.8,z,this.mat.light,sub);for(let k=0;k<4;k++)this.cyl(.4,.4,.12,x,3.3+k*.28,z,this.mat.dark,sub);}}
  for(const x of [-8,8])this.beam([x,0,-6],[x,8,-6],.35,this.mat.steel,sub);this.beam([-8,8,-6],[8,8,-6],.4,this.mat.steel,sub);
  for(const x of [-5,0,5])this.beam([x,8,-6],[x,5,0],.055,this.mat.dark,sub);
  this.subLamp=this.cyl(.3,.3,.2,0,8.5,-6,this.material('#6bd4bd'),sub);
 }
 buildDetails(){
  let seed=48;const rand=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296};
  const rockGeo=new THREE.DodecahedronGeometry(1,0);const rockMat=this.mat.rock;
  for(let i=0;i<180;i++){
   let x=rand()*198-99,z=rand()*122-61,rr=Math.hypot((x+37)/53,z/48);
   if(rr<1.08||x>15)continue;
   let r=this.mesh(rockGeo,rockMat);let scale=.25+rand()*.9;r.scale.set(scale,scale*.5,scale*.7);r.position.set(x,scale*.25,z);r.rotation.set(rand(),rand()*6,rand());
  }
  for(const[x,z]of[[19,5],[29,44],[55,42],[90,20],[90,-44],[-88,42]]){
   this.cyl(.13,.2,12,x,6,z,this.mat.steel);this.box(2,.25,.9,x,12,z,this.mat.dark);let l=this.box(1.8,.1,.7,x,11.82,z,this.material('#fff2d0'));l.material.emissive.set('#fff1c4');l.material.emissiveIntensity=.7;
  }
  // Fence perimeter and a small operations building.
  for(let z=-56;z<=45;z+=5){this.box(.12,2,.12,99,1,z,this.mat.steel);if(z<45)this.beam([99,1.8,z],[99,1.8,z+5],.05,this.mat.steel);}
  this.box(12,4,7,79,2,35,this.mat.light);this.box(13,.4,8,79,4.2,35,this.mat.dark);for(let x=74;x<=84;x+=3)this.box(1.8,1.3,.1,x,2.5,38.55,this.mat.glass);
 }
 addLabel(text,position,asset){const el=document.createElement('button');el.className='world-label';el.textContent=text;el.setAttribute('aria-label','Inspect '+text);el.onclick=()=>this.onSelect(asset);this.labelHost.appendChild(el);this.labels.push({el,position:new THREE.Vector3(...position),asset});}
 select(id){this.selected=id;}
 update(s,fresh){if(!s)return;if(this.state?.sequence===s.sequence){this.fresh=fresh;return;}this.previous=this.state;this.state=s;this.received=performance.now();this.fresh=fresh;}
 point(t){const key=t.face+t.route+t.material;const curve=this.paths[key]||this.paths['face-westroad-mainore'];let p=curve.getPointAt(Math.max(0,Math.min(1,t.position)));let dir=curve.getTangentAt(Math.max(0,Math.min(1,t.position)));const n=new THREE.Vector3(-dir.z,0,dir.x).normalize();p.addScaledVector(n,t.state==='empty_return'?-1.25:1.25);
  if(['queue_at_shovel','loading'].includes(t.state)){p.set(...this.faces[t.face]);p.z+=(Number(t.id.slice(-2))%3)*2.2;p.x-=t.state==='queue_at_shovel'?3:0;dir.set(1,0,0);}
  if(t.state==='parked'){p.set(82,1,20+Number(t.id.slice(-2))*2.5);dir.set(1,0,0);}
  return {p,dir};
 }
 animate(){requestAnimationFrame(()=>this.animate());this.controls.update();const s=this.state,now=performance.now();
  if(s){let blend=Math.min(1,(now-this.received)/800);const moving=s.status==='running'&&this.fresh;const renderMinute=moving&&this.previous&&this.previous.minute<=s.minute?THREE.MathUtils.lerp(this.previous.minute,s.minute,blend):s.minute;
   for(let i=0;i<this.trucks.length;i++){const t=s.trucks[i],obj=this.trucks[i];if(!t)continue;let point=this.point(t);let old=this.previous?.trucks[i];if(old&&old.face===t.face&&old.route===t.route&&old.state===t.state&&moving){let prior=this.point(old);point.p.lerpVectors(prior.p,point.p,blend);}
    obj.group.position.copy(point.p);obj.group.rotation.y=-Math.atan2(point.dir.z,point.dir.x)+(t.state==='empty_return'?Math.PI:0);
    obj.ore.visible=t.payload>.01;obj.ore.scale.y=.08+.40*t.payload/220;
    const dumping=['dumping','dumping_waste'].includes(t.state);obj.bed.rotation.z=dumping?Math.sin((old&&old.state===t.state&&moving?THREE.MathUtils.lerp(old.stage_progress,t.stage_progress,blend):t.stage_progress)*Math.PI)*.72:0;
    obj.dust.visible=moving&&['loaded_haul','empty_return'].includes(t.state);obj.beacon.material.color.set(t.state==='maintenance'?'#eb6347':'#e9aa43');
    for(const w of obj.wheels)w.rotation.y=moving&&t.speed?(-s.minute*15):0;
   }
   this.pile.scale.y=Math.max(.08,s.rom_t/8000);this.pile.position.y=.6+4*this.pile.scale.y;
   this.closure.visible=s.road_main_closed;this.crusherLamp.material.color.set(s.crusher_state==='fault'?'#e76043':'#66cfb2');this.subLamp.material.color.set(s.scenario==='power-limit'?'#ea9e43':'#66cfb2');
   for(const ex of this.excavators){const loading=s.trucks.some(t=>t.state==='loading'&&(t.face==='face-east'?1:0)===ex.index);ex.turret.rotation.y=loading?Math.sin(renderMinute*2)*.38:0;ex.arm.rotation.z=loading?Math.sin(renderMinute*3)*.12:0;}
   for(const part of this.beltPieces){part.mesh.visible=s.feed_rate>0;let phase=(part.offset+renderMinute*.18)%1;part.mesh.position.lerpVectors(part.a,part.b,phase);part.mesh.position.y+=.9;}
  }
  if(this.selectionRing&&s){let t=s.trucks.find(t=>t.id===this.selected);let pos=t?this.point(t).p:null;const staticPos={'pit':[-37,-23.4,0],'rom-01':[40,1,29],'crusher-01':[59,.5,5],'concentrator-01':[74,.5,-30],'substation-01':[35,.5,-39],'shovel-01':[-52,-22,1],'shovel-02':[-26,-22,-12]};if(!pos&&staticPos[this.selected])pos=new THREE.Vector3(...staticPos[this.selected]);this.selectionRing.visible=!!pos;if(pos){this.selectionRing.position.copy(pos);this.selectionRing.position.y+=.25;this.selectionRing.scale.setScalar(t?1:1.7);}}
  const occupied=[];for(const l of this.labels){let v=l.position.clone().project(this.camera);let x=(v.x*.5+.5)*this.host.clientWidth,y=(-v.y*.5+.5)*this.host.clientHeight;const collide=occupied.some(p=>Math.abs(p[0]-x)<125&&Math.abs(p[1]-y)<28);const visible=v.z<1&&x>60&&x<this.host.clientWidth-50&&y>150&&y<this.host.clientHeight-35&&!collide;l.el.style.display=visible?'block':'none';if(visible){l.el.style.left=x+'px';l.el.style.top=y+'px';occupied.push([x,y]);}}
  this.renderer.render(this.scene,this.camera);
 }
}
