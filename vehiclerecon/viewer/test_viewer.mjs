import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve(process.argv[2]);
const port=Number(process.argv[3]);
const projectConfig=JSON.parse(fs.readFileSync(path.join(root,'project.json'),'utf8'));
const fitLimit=projectConfig.viewer.fit_margin+.02;
let targets;
for(let attempt=0;attempt<40;attempt++){try{targets=await(await fetch(`http://127.0.0.1:${port}/json`)).json();break;}catch{await new Promise(r=>setTimeout(r,500));}}
if(!targets)throw Error('Isolated preview browser did not start');
const target=targets.find(t=>t.type==='page');
if(!target)throw Error('No preview browser page');
const socket=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>socket.addEventListener('open',r,{once:true}));
let next=1;const pending=new Map();socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(!p)return;pending.delete(m.id);if(m.error)p.reject(Error(JSON.stringify(m.error)));else p.resolve(m.result);}});
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=next++;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async(expression,awaitPromise=false)=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await call('Page.enable');await call('Runtime.enable');
await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url:'file:///'+root.replaceAll('\\','/')+'/output/viewer.html'});
await evaluate(`new Promise((resolve,reject)=>{const start=performance.now();const timer=setInterval(()=>{if(window.__viewerQA?.ready){clearInterval(timer);resolve(true)}else if(window.__viewerQA?.errors?.length){clearInterval(timer);reject(Error(window.__viewerQA.errors.join('; ')))}else if(performance.now()-start>30000){clearInterval(timer);reject(Error('Viewer load timeout'))}},50)})`,true);
const frame=()=>evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(true))))',true);
await frame();
const result={desktop:{},mobile:{},interaction:{}};
result.desktop.initial=await evaluate('({...__viewerQA,boundsNDC:__viewerQA.boundsNDC()})');
const expected=JSON.parse(fs.readFileSync(path.join(root,'validation/glb_geometry_report.json'),'utf8'));
if(result.desktop.initial.model.triangles!==expected.triangles)throw Error('Viewer triangle count differs from exported GLB');
if(result.desktop.initial.glbSHA256!==expected.glb_sha256)throw Error('Embedded model digest mismatch');
function fitted(bounds){return bounds.min.every(v=>v>=-fitLimit)&&bounds.max.every(v=>v<=fitLimit);}
if(!fitted(result.desktop.initial.boundsNDC))throw Error('Initial desktop framing clips the model');
let shot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(root,'validation/viewer_desktop.png'),Buffer.from(shot.data,'base64'));
for(const view of ['front','side','rear','top','three']){
    await evaluate(`document.querySelector('[data-view="${view}"]').click()`);await frame();
    const q=await evaluate('({state:__viewerQA.state,bounds:__viewerQA.boundsNDC()})');
    if(q.state.view!==view||!fitted(q.bounds))throw Error('View or fit failed: '+view);result.desktop[view]=q;
}
for(const group of projectConfig.viewer.groups.map(g=>g.id)){
    const before=await evaluate('__viewerQA.drawnTriangles');await evaluate(`document.querySelector('[data-group="${group}"]').click()`);await frame();
    const q=await evaluate('({visibility:__viewerQA.visibility,triangles:__viewerQA.drawnTriangles})');
    if(q.visibility[group]!==false||q.triangles>=before)throw Error('Layer toggle failed: '+group);
    result.interaction[group]={before,after:q.triangles};await evaluate(`document.querySelector('[data-group="${group}"]').click()`);await frame();
}
const canvas=await evaluate('(()=>{const r=document.querySelector("canvas").getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()');
const x=canvas.x+canvas.width*.5,y=canvas.y+canvas.height*.5;
const initialTheta=await evaluate('__viewerQA.state.theta');
await call('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});
await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:x+80,y:y+20,button:'left',buttons:1});
await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:x+80,y:y+20,button:'left',clickCount:1});await frame();
result.interaction.orbit=await evaluate('__viewerQA.state.theta');if(result.interaction.orbit===initialTheta)throw Error('Orbit drag failed');
const oldZoom=await evaluate('__viewerQA.state.zoom');await call('Input.dispatchMouseEvent',{type:'mouseWheel',x,y,deltaX:0,deltaY:180});await frame();
result.interaction.wheelZoom=await evaluate('__viewerQA.state.zoom');if(result.interaction.wheelZoom===oldZoom)throw Error('Wheel zoom failed');
await evaluate('document.querySelector("#fit").click()');await frame();if(await evaluate('__viewerQA.state.zoom')!==1)throw Error('Fit button failed');
await evaluate('document.querySelector("#reset").click()');await frame();if(await evaluate('__viewerQA.state.view')!=='three')throw Error('Reset failed');
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:2,mobile:true});await call('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:2});await frame();
result.mobile.initial=await evaluate('({state:__viewerQA.state,boundsNDC:__viewerQA.boundsNDC(),scrollWidth:document.documentElement.scrollWidth,width:innerWidth,errors:__viewerQA.errors})');
if(!fitted(result.mobile.initial.boundsNDC)||result.mobile.initial.scrollWidth>390)throw Error('Mobile layout or framing failed');
shot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(root,'validation/viewer_mobile.png'),Buffer.from(shot.data,'base64'));
const mobileCanvas=await evaluate('(()=>{const r=document.querySelector("canvas").getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()');
const cx=mobileCanvas.width/2,cy=mobileCanvas.y+mobileCanvas.height/2;
await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:cx-40,y:cy,id:1},{x:cx+40,y:cy,id:2}]});
await call('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:cx-65,y:cy,id:1},{x:cx+65,y:cy,id:2}]});
await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await frame();
result.interaction.pinchZoom=await evaluate('__viewerQA.state.zoom');if(!(result.interaction.pinchZoom<1))throw Error('Pinch zoom failed');
await evaluate('document.querySelector("#reset").click()');await frame();
result.errors=await evaluate('__viewerQA.errors');if(result.errors.length)throw Error(result.errors.join('; '));
result.status='PASS';result.geometry_matches_glb=true;result.glb_sha256=expected.glb_sha256;
fs.writeFileSync(path.join(root,'validation/viewer_qa.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify({status:result.status,triangles:result.desktop.initial.model.triangles,groups:result.desktop.initial.model.groups,interactions:result.interaction},null,2));
socket.send(JSON.stringify({id:next++,method:'Browser.close'}));
await new Promise(r=>{socket.addEventListener('close',r,{once:true});setTimeout(r,2000)});
socket.close();
