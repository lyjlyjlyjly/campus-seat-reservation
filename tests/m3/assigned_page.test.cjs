// 运行真实脚本；DOM/fetch 替身仅验证页面逻辑，不代表浏览器或真实登录验收。
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {mountAssigned}=require('../../web/assets/m3/assigned.js');
class Element {
  constructor(tag='') { this.tag=tag; this.children=[]; this.listeners={}; this.dataset={}; this.value=''; this.hidden=true; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children=nodes; }
  setAttribute(name,value) { this[name]=value; }
  addEventListener(name,fn) { this.listeners[name]=fn; }
}
const response=(status,data)=>({status,ok:status>=200&&status<300,json:async()=>data});
const row=(overrides={})=>({id:41,room_id:10,room_name:'<img src=x onerror=alert(1)>',fault_type:'OTHER',status:'ASSIGNED',
  created_at:'2026-11-18T16:00:00Z',assigned_at:'2026-11-18T16:00:00Z',started_at:null,updated_at:'2026-11-18T16:00:00Z',can_start:true,...overrides});
const list=(items=[row()])=>response(200,{items,total:items.length});
const success=()=>response(200,{id:41,status:'IN_REPAIR',started_at:'2026-11-18T16:00:00Z',updated_at:'2026-11-18T16:00:00Z'});
const nodes=node=>[node,...node.children.flatMap(nodes)];
function fixture(fetcher,login=false) {
  const e=Object.fromEntries(['assigned-page','assigned-message','assigned-login','assigned-status','reload-assigned','assigned-content'].map(id=>[id,new Element()]));
  e['assigned-page'].dataset.loginAvailable=String(login);
  const app=mountAssigned({getElementById:id=>e[id],createElement:tag=>new Element(tag)},fetcher);
  return {e,app,reload:()=>e['reload-assigned'].listeners.click(),filter:()=>e['assigned-status'].listeners.change(),
    buttons:()=>nodes(e['assigned-content']).filter(n=>n.tag==='button'),text:()=>nodes(e['assigned-content']).map(n=>n.textContent||'').join('\n')};
}

test('loads safe text/Beijing time and posts exactly once with empty object, then shows summary',async()=>{
  let finish,posts=0;
  const f=fixture(async(url,opts)=>{
    if(opts.method!=='POST') { assert.equal(url,'/m3/work-orders/assigned'); return list(); }
    posts++; assert.equal(url,'/m3/work-orders/41/start'); assert.equal(opts.body,'{}'); assert.equal(opts.credentials,'same-origin');
    return new Promise(resolve=>{finish=resolve;});
  });
  assert.equal(f.e['reload-assigned'].disabled,true);
  await f.app.ready;
  assert.ok(f.text().includes(row().room_name));
  assert.match(f.text(),/2026-11-19 00:00:00（北京时间）/);
  assert.match(f.text(),/开始：未记录/);
  assert.equal(nodes(f.e['assigned-content']).find(n=>n.tag==='a').href,'/m3/orders/41');
  const button=f.buttons()[0]; const sending=button.listeners.click(); await button.listeners.click();
  assert.equal(posts,1); assert.equal(button.disabled,true); assert.equal(f.e['assigned-status'].disabled,true);
  finish(success()); await sending;
  assert.equal(f.buttons().length,0); assert.match(f.text(),/维修中/);
  assert.match(f.text(),/开始：2026-11-19 00:00:00/);
  assert.equal(f.e['assigned-message'].dataset.kind,'success');
  assert.equal(f.e['reload-assigned'].disabled,false);
});

test('read-only and in-repair records offer details without a start action',async()=>{
  const f=fixture(async()=>list([row({can_start:false}),row({id:42,status:'IN_REPAIR',can_start:true})]));
  await f.app.ready;
  assert.equal(f.buttons().length,0);
  assert.equal(nodes(f.e['assigned-content']).filter(n=>n.tag==='a').length,2);
});

test('empty list/filter and successful start remove item from ASSIGNED view',async()=>{
  const urls=[];
  const f=fixture(async(url,opts)=>{
    urls.push(url);
    if(opts.method==='POST') return success();
    if(url.endsWith('IN_REPAIR')) return list([]);
    return list();
  });
  await f.app.ready;
  f.e['assigned-status'].value='IN_REPAIR'; await f.filter();
  assert.match(f.text(),/暂无本人受理工单/);
  f.e['assigned-status'].value='ASSIGNED'; await f.filter();
  await f.buttons()[0].listeners.click();
  assert.match(f.text(),/暂无本人受理工单/);
  assert.ok(urls.includes('/m3/work-orders/assigned?status=ASSIGNED'));
  assert.ok(urls.includes('/m3/work-orders/assigned?status=IN_REPAIR'));
});

test('401/403/503 clear old private content and show login only when real login is installed',async()=>{
  for(const [status,login,hidden] of [[401,false,true],[401,true,false],[403,true,true],[503,true,true]]) {
    let revoked=false;
    const f=fixture(async()=>revoked?response(status,{error:'blocked',message:'<b>不可访问</b>'}):list(),login);
    await f.app.ready; const old=f.buttons()[0]; revoked=true; await f.reload();
    assert.equal(f.e['assigned-content'].children.length,0); assert.equal(f.buttons().length,0);
    assert.equal(f.e['assigned-login'].hidden,hidden);
    assert.ok(f.e['assigned-message'].textContent.startsWith('<b>不可访问</b>'));
    await old.listeners.click(); // 即使调用旧事件闭包，也不能绕过已清空的列表状态。
    assert.equal(f.buttons().length,0);
  }
});

test('409 refreshes current state without another POST',async()=>{
  let posts=0,gets=0;
  const f=fixture(async(url,opts)=>{
    if(opts.method==='POST') { posts++; return response(409,{error:'conflict',message:'已开始'}); }
    gets++; return list([row(posts?{status:'IN_REPAIR',can_start:false,started_at:'2026-11-18T16:00:00Z'}:{})]);
  });
  await f.app.ready; await f.buttons()[0].listeners.click();
  assert.equal(posts,1); assert.equal(gets,2); assert.equal(f.buttons().length,0);
  assert.match(f.e['assigned-message'].textContent,/状态已变化/); assert.match(f.text(),/维修中/);
});

test('POST auth failure and known unavailable/busy errors clear private operation entries',async()=>{
  for(const [status,error] of [[401,'unauthenticated'],[403,'forbidden'],[503,'database_busy'],[503,'auth_unavailable']]) {
    const f=fixture(async(url,opts)=>opts.method==='POST'?response(status,{error,message:'本次不可开始'}):list());
    await f.app.ready; const button=f.buttons()[0]; await button.listeners.click();
    assert.equal(f.e['assigned-content'].children.length,0);
    assert.equal(f.e['assigned-message'].dataset.kind,'error');
    assert.equal(f.e['reload-assigned'].disabled,false);
  }
});

test('unknown network/json/server/shape result never auto retries, including after manual query',async()=>{
  for(const mode of ['network','json','server','shape']) {
    let posts=0;
    const f=fixture(async(url,opts)=>{
      if(opts.method!=='POST') return list();
      posts++;
      if(mode==='network') throw new Error('offline');
      if(mode==='json') return {status:200,ok:true,json:async()=>{throw new Error('unreadable');}};
      if(mode==='server') return response(500,{error:'internal_error',message:'服务错误'});
      return response(200,{});
    });
    await f.app.ready; const button=f.buttons()[0]; await button.listeners.click(); await button.listeners.click();
    assert.equal(posts,1); assert.equal(button.disabled,true);
    assert.match(f.e['assigned-message'].textContent,/结果不明/);
    await f.reload(); await f.buttons()[0].listeners.click();
    assert.equal(posts,1); assert.equal(f.buttons()[0].disabled,true);
    assert.match(f.e['assigned-message'].textContent,/核实上次操作/);
  }
});

test('conflict refresh losing authorization clears links and does not refill stale data',async()=>{
  let posted=false;
  const f=fixture(async(url,opts)=>{
    if(opts.method==='POST') { posted=true; return response(409,{error:'conflict',message:'冲突'}); }
    return posted?response(403,{error:'forbidden',message:'读取权限已撤销'}):list();
  });
  await f.app.ready; await f.buttons()[0].listeners.click();
  assert.equal(f.e['assigned-content'].children.length,0);
  assert.equal(f.e['assigned-message'].textContent,'读取权限已撤销');
});

test('read network/invalid body leaves no private actions and permits a manual reload',async()=>{
  for(const mode of ['network','shape']) {
    const f=fixture(async()=>{ if(mode==='network') throw new Error('offline'); return list([row({id:'41'})]); });
    await f.app.ready;
    assert.equal(f.e['assigned-content'].children.length,0);
    assert.equal(f.e['assigned-message'].dataset.kind,'error');
    assert.equal(f.e['reload-assigned'].disabled,false);
  }
});
