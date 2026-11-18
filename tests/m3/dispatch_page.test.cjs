// 运行实际派单脚本；DOM/fetch 仅替换 UI I/O，不是实际浏览器或共享登录验收。
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {mountDispatch} = require('../../web/assets/m3/dispatch.js');

class Element {
  constructor(tag='') { this.tag=tag; this.value=''; this.children=[]; this.dataset={}; this.listeners={}; this.hidden=true; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children=nodes; this.value=''; }
  setAttribute(name,value) { this[name]=value; }
  removeAttribute(name) { delete this[name]; }
  addEventListener(name,listener) { this.listeners[name]=listener; }
}
const response = (status,body) => ({status,ok:status>=200&&status<300,json:async()=>body});
const row = (state='REPORTED') => ({id:41,room_id:10,room_name:'<img src=x onerror=alert(1)>',fault_type:'OTHER',status:state,created_at:'2026-11-18T20:30:00Z',assigned_to:null,assigned_at:null,detail_url:'javascript:untrusted'});
const queue = (rows=[row()]) => response(200,{items:rows,total:rows.length});
const candidates = (rows=[{id:4,display_name:'<script>alert(1)</script>'}]) => response(200,{items:rows});
const success = () => response(200,{id:41,status:'ASSIGNED',assigned_to:4,assigned_at:'2026-11-18T20:40:00Z'});
function fixture(fetcher,login=false) {
  const ids=['dispatch-page','dispatch-message','dispatch-login','dispatch-status','reload-dispatch','dispatch-content','assignment-form','assignment-fields','submit-assignment','dispatch-order','assigned-to','assignment-detail','queue-message','repairers-message'];
  const e=Object.fromEntries(ids.map(id=>[id,new Element()]));
  e['dispatch-page'].dataset.loginAvailable=String(login); e['dispatch-status'].value='REPORTED';
  const page=mountDispatch({getElementById:id=>e[id],createElement:tag=>new Element(tag)},fetcher);
  return {e,page,select:()=>{e['dispatch-order'].value='41';e['assigned-to'].value='4';},submit:()=>e['assignment-form'].listeners.submit({preventDefault(){}}),reload:()=>e['reload-dispatch'].listeners.click(),filter:()=>e['dispatch-status'].listeners.change()};
}

test('loading and pending submit disable repeats, success refreshes queue and links exact detail',async()=>{
  let resolvePost,posts=0,reads=0;
  const f=fixture(async(url,options)=>{
    if(url==='/m3/repairers') return candidates();
    if(options.method!=='POST') { reads++; return queue(posts ? [] : [row()]); }
    posts++;
    assert.equal(url,'/m3/work-orders/41/assign');
    assert.deepEqual(JSON.parse(options.body),{assigned_to:4});
    assert.equal(options.credentials,'same-origin');
    return new Promise(resolve=>{resolvePost=resolve;});
  });
  assert.equal(f.e['submit-assignment'].disabled,true);
  assert.match(f.e['dispatch-message'].textContent,/正在加载/);
  await f.page.ready;
  const nodes=f.e['dispatch-content'].children[0].children[0].children;
  assert.equal(nodes[0].textContent,'#41 · '+row().room_name);
  assert.match(nodes[2].textContent,/2026-11-19 04:30:00（北京时间）/);
  assert.equal(nodes[3].href,'/m3/orders/41'); // 不信任服务端提供的任意 URL。
  assert.equal(f.e['assigned-to'].children[1].textContent,'<script>alert(1)</script>（#4）');
  f.select(); const sending=f.submit(); await f.submit();
  assert.equal(posts,1); assert.equal(f.e['submit-assignment'].disabled,true);
  assert.equal(f.e['reload-dispatch'].disabled,true);
  resolvePost(success()); await sending;
  assert.equal(reads,2); assert.match(f.e['dispatch-message'].textContent,/派单成功/);
  assert.equal(f.e['assignment-detail'].href,'/m3/orders/41');
  assert.equal(f.e['assignment-detail'].hidden,false);
  assert.equal(f.e['submit-assignment'].disabled,true); // 成功后队列为空。
});

test('status filter loads requested state and never offers reassignment',async()=>{
  const seen=[];
  const f=fixture(async(url)=>{
    seen.push(url);
    if(url==='/m3/repairers') return candidates();
    const state=new URL(url,'http://local').searchParams.get('status');
    return queue([{...row(state),assigned_to:4,assigned_at:'2026-11-18T21:00:00Z'}]);
  });
  await f.page.ready;
  for(const state of ['ASSIGNED','IN_REPAIR']) {
    f.e['dispatch-status'].value=state; await f.filter();
    assert.ok(seen.includes('/m3/work-orders/dispatch?status='+state));
    assert.equal(f.e['submit-assignment'].disabled,true);
    assert.equal(f.e['dispatch-order'].children.length,1);
    assert.match(f.e['dispatch-content'].children[0].children[0].children[3].textContent,/05:00:00（北京时间）/);
  }
});

test('empty queue or no qualified people are readable normal states with disabled assignment',async()=>{
  for(const empty of ['queue','people']) {
    const f=fixture(async url=>url==='/m3/repairers' ? candidates(empty==='people'?[]:undefined) : queue(empty==='queue'?[]:undefined));
    await f.page.ready;
    assert.equal(f.e['submit-assignment'].disabled,true);
    assert.match(f.e[empty==='people'?'repairers-message':'queue-message'].textContent,empty==='people'?/暂无合法维修人员/:/暂无工单/);
  }
});

test('401/403/503 and unavailable dependency show safe errors and only real login link',async()=>{
  for(const [status,available,hidden] of [[401,false,true],[401,true,false],[403,true,true],[503,true,true]]) {
    const f=fixture(async()=>response(status,{error:'example',message:'<b>无权或依赖不可用</b>'}),available);
    await f.page.ready;
    assert.ok(f.e['dispatch-message'].textContent.startsWith('<b>无权或依赖不可用</b>'));
    assert.equal(f.e['dispatch-login'].hidden,hidden);
    assert.equal(f.e['dispatch-content'].children.length,0);
    assert.equal(f.e['assigned-to'].children.length,0);
    assert.equal(f.e['submit-assignment'].disabled,true);
  }
});

test('late successful response cannot refill old private data after reload authorization failure',async()=>{
  let revoked=false,finish;
  const f=fixture(async url=>{
    if(!revoked) return url==='/m3/repairers'?candidates():queue();
    if(url==='/m3/repairers') return new Promise(resolve=>{finish=resolve;});
    return response(403,{error:'forbidden',message:'权限已撤销'});
  });
  await f.page.ready; assert.equal(f.e['dispatch-content'].children.length,1);
  revoked=true; const pending=f.reload();
  assert.equal(f.e['dispatch-content'].children.length,0);
  finish(candidates()); await pending;
  assert.equal(f.e['dispatch-content'].children.length,0);
  assert.equal(f.e['dispatch-order'].children.length,0);
  assert.equal(f.e['assigned-to'].children.length,0);
  assert.equal(f.e['assignment-detail'].hidden,true);
});

test('409 refreshes queue and offers detail, without automatically resending',async()=>{
  let posts=0,reads=0;
  const f=fixture(async(url,options)=>{
    if(options.method==='POST') { posts++; return response(409,{error:'conflict',message:'工单状态已变化'}); }
    if(url==='/m3/repairers') return candidates();
    reads++; return queue(posts?[]:undefined);
  });
  await f.page.ready; f.select(); await f.submit();
  assert.equal(posts,1); assert.equal(reads,2);
  assert.match(f.e['dispatch-message'].textContent,/状态已变化/);
  assert.equal(f.e['assignment-detail'].href,'/m3/orders/41');
  assert.equal(f.e['submit-assignment'].disabled,true);
});

test('422 reloads candidates after qualification change and retains refusal message',async()=>{
  let posts=0,peopleReads=0,queueReads=0;
  const f=fixture(async(url,options)=>{
    if(options.method==='POST') { posts++; return response(422,{error:'invalid_repairer',message:'所选人员已失去资格'}); }
    if(url==='/m3/repairers') { peopleReads++; return candidates(posts?[]:undefined); }
    queueReads++; return queue();
  });
  await f.page.ready; f.select(); await f.submit();
  assert.equal(posts,1); assert.equal(peopleReads,2); assert.equal(queueReads,1);
  assert.equal(f.e['dispatch-message'].textContent,'所选人员已失去资格');
  assert.match(f.e['repairers-message'].textContent,/暂无合法维修人员/);
});

test('unknown POST result never claims success or failure, even after manual read refresh',async()=>{
  for(const failure of ['network','json','shape','server']) {
    let posts=0;
    const f=fixture(async(url,options)=>{
      if(options.method!=='POST') return url==='/m3/repairers'?candidates():queue();
      posts++;
      if(failure==='network') throw new Error('connection lost');
      if(failure==='json') return {status:200,ok:true,json:async()=>{throw new Error('unreadable');}};
      if(failure==='server') return response(500,{error:'internal_error',message:'内部错误'});
      return response(200,{});
    });
    await f.page.ready; f.select(); await f.submit(); await f.submit();
    assert.equal(posts,1); assert.match(f.e['dispatch-message'].textContent,/结果不明/);
    assert.equal(f.e['assignment-detail'].href,'/m3/orders/41');
    await f.reload(); f.select(); await f.submit();
    assert.equal(posts,1); assert.equal(f.e['submit-assignment'].disabled,true);
    assert.equal(f.e['assignment-detail'].hidden,false);
  }
});

test('POST authentication loss clears private data and busy rollback never reports success',async()=>{
  for(const [status,code] of [[401,'unauthenticated'],[403,'forbidden'],[503,'database_busy'],[503,'auth_unavailable']]) {
    const f=fixture(async(url,options)=>options.method==='POST'?response(status,{error:code,message:'本次不可派单'}):(url==='/m3/repairers'?candidates():queue()));
    await f.page.ready; f.select(); await f.submit();
    assert.equal(f.e['dispatch-message'].dataset.kind,'error');
    assert.equal(f.e['dispatch-content'].children.length,0);
    assert.equal(f.e['assigned-to'].children.length,0);
    assert.equal(f.e['assignment-detail'].hidden,true);
    assert.equal(f.e['submit-assignment'].disabled,true);
  }
});

test('successful write followed by failed reload does not restore private link or stale queue',async()=>{
  let posted=false;
  const f=fixture(async(url,options)=>{
    if(options.method==='POST') { posted=true; return success(); }
    if(posted) return response(403,{error:'forbidden',message:'权限已撤销'});
    return url==='/m3/repairers'?candidates():queue();
  });
  await f.page.ready; f.select(); await f.submit();
  assert.equal(f.e['dispatch-content'].children.length,0);
  assert.equal(f.e['assignment-detail'].hidden,true);
  assert.equal(f.e['dispatch-message'].textContent,'权限已撤销');
});

test('read network and malformed candidates leave no old data and allow manual refresh',async()=>{
  for(const bad of ['network','shape']) {
    let calls=0;
    const f=fixture(async url=>{
      calls++;
      if(url==='/m3/repairers') {
        if(bad==='network') throw new Error('offline');
        return response(200,{items:[{id:'4',display_name:'invalid id'}]});
      }
      return queue();
    });
    await f.page.ready;
    assert.equal(calls,2); assert.equal(f.e['dispatch-message'].dataset.kind,'error');
    assert.equal(f.e['dispatch-content'].children.length,0);
    assert.equal(f.e['reload-dispatch'].disabled,false);
  }
});
