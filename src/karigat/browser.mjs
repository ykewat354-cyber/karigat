// Inspect a trusted localhost preview in a fresh, disposable browser profile.
import {spawn} from 'node:child_process';
import {writeFileSync,readFileSync} from 'node:fs';
const [url,out,journey,postPath]=process.argv.slice(2), origin=new URL(url).origin;
if(new URL(url).hostname!=='127.0.0.1')throw Error('Local preview required');
const proc=spawn('proot-distro',['login','--isolated','debian','--','chromium','--headless','--no-sandbox','--no-first-run','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--disable-extensions','--disable-sync','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0',`--user-data-dir=/tmp/karigat-${process.pid}`, 'about:blank'],{stdio:['ignore','ignore','pipe'],detached:true});
let ws,id=0,session;const waits=new Map(),errors=[];
function send(method,params={},sid=session){return new Promise((resolve,reject)=>{let n=++id;waits.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params,sessionId:sid}));});}
function stop(){try{ws?.close();process.kill(-proc.pid,'SIGTERM');}catch{}}
const timer=setTimeout(()=>{stop();console.error('Browser inspection timed out');process.exit(2);},45000);
try{
 const endpoint=await new Promise((ok,no)=>{let log='';proc.on('error',no);proc.on('exit',()=>no(Error('Browser closed')));proc.stderr.on('data',b=>{log=(log+b).slice(-2048);let m=log.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(m)ok(m[1]);});});
 ws=new WebSocket(endpoint);await new Promise((ok,no)=>{ws.onopen=ok;ws.onerror=no});
 ws.onmessage=({data})=>{let m=JSON.parse(data);if(m.id){let p=waits.get(m.id);if(p){waits.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}}else if(m.method==='Fetch.requestPaused'){let q=m.params.request;let allowed=new URL(q.url).origin===origin && (q.method==='GET'||(q.method==='POST'&&postPath&&new URL(q.url).pathname===postPath));send(allowed?'Fetch.continueRequest':'Fetch.failRequest',allowed?{requestId:m.params.requestId}:{requestId:m.params.requestId,errorReason:'BlockedByClient'},m.sessionId).catch(()=>{});}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);};
 const {targetId}=await send('Target.createTarget',{url:'about:blank'});session=(await send('Target.attachToTarget',{targetId,flatten:true})).sessionId;
 for (const d of ['Runtime','Page','Fetch'])await send(d+'.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await send('Page.navigate',{url});
 const evaluate=async(expression)=>(await send('Runtime.evaluate',{expression,returnByValue:true})).result.value;
 for(let n=0;n<100;n++){if(await evaluate(`location.origin===${JSON.stringify(origin)} && document.readyState==='complete'`))break;await new Promise(r=>setTimeout(r,80));}
 const layout=[];
 for(const width of [320,360,768,390]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:844,deviceScaleFactor:1,mobile:true});await new Promise(r=>setTimeout(r,100));
  const issues=await evaluate(`(()=>{const problems=[];if(document.documentElement.scrollWidth>${width}+1)problems.push('page wider than viewport');for(const bar of document.querySelectorAll('nav,header,[role="navigation"]')){const s=getComputedStyle(bar),b=bar.getBoundingClientRect();if(!['fixed','sticky'].includes(s.position)||b.height<1||b.top>5)continue;for(const el of bar.querySelectorAll('a,button')){const r=el.getBoundingClientRect();if(r.width<1||r.height<1||getComputedStyle(el).visibility==='hidden')continue;if(r.width>0 && (r.top< -1||r.right>${width}+1||r.left< -1))problems.push('clipped: '+(el.innerText||el.ariaLabel).trim().slice(0,50));}}return problems})()`);layout.push({width,issues});
  if(issues.includes('page wider than viewport'))layout.at(-1).overflowSamples=await evaluate(`[...document.body.querySelectorAll('*')].filter(e=>{const b=e.getBoundingClientRect();for(let p=e.parentElement;p&&p!==document.body;p=p.parentElement)if(['auto','hidden','clip','scroll'].includes(getComputedStyle(p).overflowX))return false;return b.width>0&&b.right>${width}+1 && getComputedStyle(e).visibility!=='hidden'}).slice(0,20).map(e=>[e.tagName,e.className?.toString(),Math.round(e.getBoundingClientRect().right)])`);
 }
 const metrics=await evaluate(`({title:document.title,heading:document.querySelector('h1')?.innerText||'',horizontalOverflow:document.documentElement.scrollWidth>390,buttons:document.querySelectorAll('button').length,links:document.links.length,textLength:document.body.innerText.length})`);
 const img=await send('Page.captureScreenshot',{format:'png'});writeFileSync(out,Buffer.from(img.data,'base64'));
 const anchor=await evaluate(`(()=>{const a=[...document.links].find(x=>x.getAttribute('href')?.startsWith('#') && document.getElementById(x.hash.slice(1)));if(!a)return null; a.click();return a.hash;})()`);
 if(anchor)await new Promise(r=>setTimeout(r,700));
 const navVisible=anchor?await evaluate(`(()=>{const b=document.getElementById(${JSON.stringify(anchor.slice(1))}).getBoundingClientRect(); return b.bottom>0 && b.top<innerHeight})()`):null;
 const steps=[];
 if(journey){for(const step of JSON.parse(readFileSync(journey,'utf8'))){let ok=false;const sel=JSON.stringify(step.selector||'body'),val=JSON.stringify(step.value||'');
  if(step.op==='fill')ok=await evaluate(`(()=>{const e=document.querySelector(${sel});if(!e)return false;e.value=${val};e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return e.value===${val}})()`);
  if(step.op==='first-screen'){const pos=await evaluate(`(()=>{scrollTo({top:0,behavior:'instant'});const e=document.querySelector(${sel});if(!e)return null;const b=e.getBoundingClientRect();return {bottom:Math.round(b.bottom),viewport:innerHeight,visible:b.width>0&&b.height>0&&b.top>=0&&b.bottom<=innerHeight&&e.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2))}})()`);ok=pos?.visible;step.measurement=pos;}
  if(step.op==='click')ok=await evaluate(`(()=>{const e=document.querySelector(${sel});if(!e||e.disabled||!e.getClientRects().length)return false;e.scrollIntoView({block:'center',behavior:'instant'});const b=e.getBoundingClientRect();if(!e.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2)))return false;e.click();return true})()`);
  if(step.op==='reload'){await send('Page.reload');ok=true;await new Promise(r=>setTimeout(r,350));}
  if(step.op==='turntable'){
   const box=await evaluate(`(()=>{const b=document.querySelector(${sel})?.getBoundingClientRect();return b&&{x:b.x+b.width*.25,y:b.y+b.height*.25,width:b.width*.5,height:b.height*.5,scale:1}})()`);
   if(box?.width>8&&box?.height>8){
    const delay=ms=>new Promise(r=>setTimeout(r,ms));const frame=async()=>(await send('Page.captureScreenshot',{format:'png',clip:box})).data;
    const button=label=>evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(e=>(e.innerText+' '+e.ariaLabel).toLowerCase().includes(${JSON.stringify(label)}));if(!b||b.disabled)return false;b.click();return true})()`);
    const first=await frame();await delay(450);const moving=first!==await frame();const paused=await button('pause');await delay(120);const frozen=await frame();await delay(450);const stable=await frame()===frozen;
    const x=box.x+box.width*.45,y=box.y+box.height*.45;
    for(const [type,offset] of [['mousePressed',0],['mouseMoved',28],['mouseMoved',65],['mouseReleased',65]])await send('Input.dispatchMouseEvent',{type,x:x+offset,y,button:'left',buttons:type==='mouseReleased'?0:1});
    await delay(120);const afterDrag=await frame();const dragged=afterDrag!==frozen;
    // Compare two deterministic reset frames; does not claim an exact angle from pixels.
    const reset=await button('reset');await delay(80);const reset1=await frame();await button('reset');await delay(80);const repeatable=await frame()===reset1;
    step.measurement={moving,paused,stable,dragged,reset,restoredDifferentView:reset1!==afterDrag,repeatable};ok=Object.values(step.measurement).every(Boolean);
   }
  }
  if(step.op==='painted'){
   // Sample the actual composited viewport, not the WebGL drawing buffer (which may be cleared).
   const rect=await evaluate(`(()=>{const b=document.querySelector(${sel})?.getBoundingClientRect();if(!b)return null;const x=Math.max(0,b.left),y=Math.max(0,b.top),w=Math.min(innerWidth,b.right)-x,h=Math.min(innerHeight,b.bottom)-y;return w>=8&&h>=8?{x:x+w*.1+scrollX,y:y+h*.1+scrollY,width:w*.8,height:h*.8,scale:1}:null})()`);
   if(rect){const shot=await send('Page.captureScreenshot',{format:'png',clip:rect});
    const measurement=await send('Runtime.evaluate',{awaitPromise:true,returnByValue:true,expression:`(async()=>{const im=new Image();im.src='data:image/png;base64,${shot.data}';await im.decode();const c=document.createElement('canvas');c.width=c.height=32;const g=c.getContext('2d');g.drawImage(im,0,0,32,32);const p=g.getImageData(0,0,32,32).data;let bins=new Map();for(let i=0;i<p.length;i+=4){const k=(p[i]>>4)*256+(p[i+1]>>4)*16+(p[i+2]>>4);bins.set(k,1+(bins.get(k)||0));}return 1024-Math.max(...bins.values())})()`});
    step.measurement={nonDominantPixels:measurement.result.value,samples:1024};ok=measurement.result.value>=16;
   }
  }
  if(step.op==='checked')ok=await evaluate(`(()=>{const e=document.querySelector(${sel});return !!e&&(e.checked===true||e.getAttribute('aria-checked')==='true'||e.getAttribute('aria-pressed')==='true')})()`);
  if(step.op==='text'){for(let n=0;n<30&&!ok;n++){ok=await evaluate(`document.querySelector(${sel})?.innerText.includes(${val})`);if(!ok)await new Promise(r=>setTimeout(r,100));}}
  steps.push({op:step.op,selector:step.selector,ok:!!ok,...(step.measurement?{measurement:step.measurement}:{})});if(!ok)break;
 }}
 const result={viewport:'390x844',layout,...metrics,anchor,navVisible,steps,errors,screenshot:out};writeFileSync(out+'.json',JSON.stringify(result,null,2)); console.log(JSON.stringify(result));process.exitCode=(!metrics.heading || !metrics.textLength || layout.some(x=>x.issues.length) || steps.some(x=>!x.ok) || navVisible===false || errors.length)?1:0;
}catch(e){console.error(e.message);process.exitCode=2;}finally{clearTimeout(timer);stop();}
