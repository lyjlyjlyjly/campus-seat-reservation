// Node 标准库运行实际页面脚本；DOM/fetch 仅作 UI I/O 替身，不是浏览器或数据库集成验收。
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { normalize, characterCount, mountReport } = require('../../web/assets/m3/report.js');

class Element {
  constructor() { this.value = ''; this.children = []; this.dataset = {}; this.listeners = {}; this.hidden = true; }
  set innerHTML(_) { throw new Error('Unsafe HTML rendering'); }
  setAttribute(name, value) { this[name] = value; }
  setCustomValidity(message) { this.validation = message; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  append(element) { this.children.push(element); }
  replaceChildren() { this.children = []; this.value = ''; }
}
function fixture(fetcher, loginAvailable = false) {
  const ids = ['report-form','report-fields','room-id','fault-type','description','description-count','submit-report','reload-rooms','report-login','report-message','created-order-link'];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  elements['report-form'].dataset.loginAvailable = String(loginAvailable);
  elements['report-form'].reportValidity = () => !elements.description.validation;
  const page = mountReport({getElementById: id => elements[id], createElement: () => new Element()}, fetcher);
  const fill = text => { elements['room-id'].value = '20'; elements['fault-type'].value = 'OTHER'; elements.description.value = text; elements.description.listeners.input(); };
  const submit = () => elements['report-form'].listeners.submit({preventDefault() {}});
  return {elements, page, fill, submit};
}
const response = (status, body) => ({status, ok: status >= 200 && status < 300, json: async () => body});
const rooms = () => response(200, {items: [{id:20, name:'<img src=x onerror=alert(1)>', is_active:0}]});

test('Unicode count matches Python whitespace semantics and never truncates non-BMP', () => {
  assert.equal(characterCount('\x1c\u0085💡\u3000'), 1);
  assert.equal(characterCount('💡'.repeat(1000)), 1000);
  assert.equal(characterCount('💡'.repeat(1001)), 1001);
  assert.equal(characterCount('\ufeff'), 1); // JS trim 会移除 BOM，Python strip 不会。
  assert.equal(normalize('  中  文\n下一行  '), '中  文\n下一行');
});

test('loads real API shape, shows inactive label, disables pending submit, renders success safely', async () => {
  let resolvePost, posts = 0;
  const f = fixture(async (url, options) => {
    if (url === '/m3/rooms') return rooms();
    posts++;
    assert.deepEqual(JSON.parse(options.body), {room_id:20, fault_type:'OTHER', description:'💡'.repeat(1000)});
    return new Promise(resolve => {resolvePost = resolve;});
  });
  await f.page.ready;
  assert.equal(f.elements['room-id'].children[1].textContent, '<img src=x onerror=alert(1)>（停借，仍可报修）');
  f.fill('💡'.repeat(1000));
  const pending = f.submit();
  assert.equal(f.elements['submit-report'].disabled, true);
  await f.submit();
  assert.equal(posts, 1);
  resolvePost(response(201, {id:41, status:'REPORTED', created_at:'2026-11-18T09:00:00Z'}));
  await pending;
  assert.match(f.elements['report-message'].textContent, /#41.*REPORTED/);
  assert.equal(f.elements['created-order-link'].href, '/m3/orders/41');
  assert.equal(f.elements['created-order-link'].hidden, false);
  assert.equal(f.elements.description.value, '💡'.repeat(1000));
});

test('422 and busy 503 keep input and permit manual correction/retry only', async () => {
  for (const status of [422, 503]) {
    let posts = 0;
    const f = fixture(async url => url === '/m3/rooms' ? rooms() : (posts++, response(status, {error: status === 422 ? 'unknown_room' : 'database_busy', message:'请稍后处理'})));
    await f.page.ready;
    f.fill('中文  内容\n换行');
    await f.submit();
    assert.equal(posts, 1);
    assert.equal(f.elements.description.value, '中文  内容\n换行');
    assert.equal(f.elements['report-message'].textContent, '请稍后处理');
    assert.equal(f.elements['submit-report'].disabled, false);
  }
});

test('network rejection or unreadable POST result blocks resubmission without auto retry', async () => {
  for (const failure of ['network','bad-json','unexpected-success']) {
    let posts = 0;
    const f = fixture(async url => {
      if (url === '/m3/rooms') return rooms();
      posts++;
      if (failure === 'network') throw new Error('connection lost');
      if (failure === 'bad-json') return {status:201, ok:true, json:async () => {throw new Error('invalid JSON');}};
      return response(200, {});
    });
    await f.page.ready;
    f.fill('保留的描述');
    await f.submit();
    await f.submit();
    assert.equal(posts, 1);
    assert.match(f.elements['report-message'].textContent, /结果不明.*请勿刷新后重复提交/);
    assert.equal(f.elements.description.value, '保留的描述');
    assert.equal(f.elements['submit-report'].disabled, true);
    assert.equal(f.elements['reload-rooms'].disabled, true);
    assert.equal(f.elements['created-order-link'].hidden, true);
    assert.equal(f.elements['created-order-link'].href, undefined);
    assert.match(f.elements['report-message'].textContent, /我的工单.*不能直接认领最新工单/);
  }
});

test('missing auth keeps page disabled and hidden login; 401 links only to installed login', async () => {
  for (const [status, available, hidden] of [[503,false,true],[401,false,true],[401,true,false],[403,true,true]]) {
    const f = fixture(async () => response(status, {error:'auth_unavailable', message:'当前暂不可提交'}), available);
    await f.page.ready;
    assert.equal(f.elements['submit-report'].disabled, true);
    assert.equal(f.elements['report-login'].hidden, hidden);
  }
});

test('overlong text blocks POST without slicing and updates visible codepoint count', async () => {
  let posts = 0;
  const f = fixture(async url => url === '/m3/rooms' ? rooms() : (posts++, response(201, {})));
  await f.page.ready;
  f.fill('💡'.repeat(1001));
  await f.submit();
  assert.equal(posts, 0);
  assert.match(f.elements['description-count'].textContent, /^1001/);
  assert.equal(f.elements.description.value, '💡'.repeat(1001));
});
