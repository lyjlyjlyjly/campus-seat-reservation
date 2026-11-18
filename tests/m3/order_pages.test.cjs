// 执行实际页面脚本；DOM/fetch 是 UI I/O 替身，不等同真实浏览器或登录联调。
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { beijingTime, mountOrders } = require('../../web/assets/m3/orders.js');

class Element {
  constructor(tag = '') { this.tag = tag; this.children = []; this.dataset = {}; this.listeners = {}; this.hidden = true; }
  set innerHTML(_) { throw new Error('Unsafe HTML rendering'); }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
}
function fixture(fetcher, {mode = 'list', login = false} = {}) {
  const ids = ['orders-page', 'orders-content', 'orders-message', 'reload-orders', 'orders-login'];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  elements['orders-page'].dataset = {mode, orderId: '41', loginAvailable: String(login)};
  const page = mountOrders({getElementById: id => elements[id], createElement: tag => new Element(tag)}, fetcher);
  return {elements, page, reload: () => elements['reload-orders'].listeners.click()};
}
const response = (status, body) => ({status, ok: status >= 200 && status < 300, json: async () => body});
const order = () => ({
  id: 41, room_id: 10, room_name: '<img src=x onerror=alert(1)>', fault_type: 'WATER', status: 'REPORTED',
  created_at: '2026-11-18T20:30:00Z', updated_at: '2026-11-18T20:30:00Z', reporter_id: 1,
  description: '<script>alert(1)</script>\n中文  💡', assigned_to: null, assigned_by: null,
  assigned_at: null, started_at: null,
});
const summary = () => response(200, {items: [order()], total: 1});

test('UTC is explicitly converted to Beijing across midnight, null/invalid time is readable', () => {
  assert.equal(beijingTime('2026-11-18T20:30:00Z'), '2026-11-19 04:30:00（北京时间）');
  assert.equal(beijingTime('2026-11-18T16:00:00Z'), '2026-11-19 00:00:00（北京时间）');
  assert.equal(beijingTime(null), '未记录');
  assert.equal(beijingTime('not-a-timeZ'), '时间不可用');
  assert.equal(beijingTime('2026-11-18T20:30:00'), '时间不可用');
});

test('pending list disables reload, success renders safe text and exact order link', async () => {
  let resolve, calls = 0;
  const f = fixture((url, options) => {
    calls++;
    assert.equal(url, '/m3/work-orders');
    assert.deepEqual(options, {credentials: 'same-origin', cache: 'no-store'});
    return new Promise(done => { resolve = done; });
  });
  assert.equal(f.elements['reload-orders'].disabled, true);
  assert.equal(f.elements['orders-page']['aria-busy'], 'true');
  assert.match(f.elements['orders-message'].textContent, /正在加载/);
  await f.reload();
  assert.equal(calls, 1);
  resolve(summary());
  await f.page.ready;
  assert.equal(f.elements['reload-orders'].disabled, false);
  assert.equal(f.elements['orders-page']['aria-busy'], 'false');
  const row = f.elements['orders-content'].children[0].children[0];
  assert.equal(row.children[0].textContent, order().room_name);
  assert.equal(row.children[1].textContent, '给排水故障 · 已报修');
  assert.match(row.children[2].textContent, /2026-11-19 04:30:00（北京时间）/);
  assert.equal(row.children[3].href, '/m3/orders/41');
  assert.equal(f.elements['orders-message'].dataset.kind, 'success');
});

test('empty list is a normal state without fabricated records or detail link', async () => {
  const f = fixture(async () => response(200, {items: [], total: 0}));
  await f.page.ready;
  assert.equal(f.elements['orders-message'].dataset.kind, 'empty');
  assert.match(f.elements['orders-message'].textContent, /暂无本人的报修工单/);
  assert.equal(f.elements['orders-content'].children.length, 0);
});

test('detail uses literal text, preserves description newlines and handles unassigned time fields', async () => {
  const f = fixture(async (url, options) => {
    assert.equal(url, '/m3/work-orders/41');
    assert.equal(options.method, undefined); // 默认 GET；页面从不发送写请求。
    return response(200, order());
  }, {mode: 'detail'});
  await f.page.ready;
  const nodes = f.elements['orders-content'].children[0].children;
  const fields = Object.fromEntries(nodes.filter((_, i) => i % 2 === 0).map((node, i) => [node.textContent, nodes[i * 2 + 1]]));
  assert.equal(fields['房间'].textContent, order().room_name);
  assert.equal(fields['故障描述'].textContent, order().description);
  assert.equal(fields['故障描述'].className, 'order-description');
  assert.equal(fields['受理人编号'].textContent, '尚未派单');
  assert.equal(fields['派单时间'].textContent, '尚未派单');
  assert.equal(fields['开始维修'].textContent, '尚未开始维修');
  assert.equal(fields['更新时间'].textContent, '2026-11-19 04:30:00（北京时间）');
});

test('assigned and repair details show existing people and UTC times, without action controls', async () => {
  const item = {...order(), status: 'IN_REPAIR', assigned_to: 2, assigned_by: 3,
    assigned_at: '2026-11-18T21:00:00Z', started_at: '2026-11-18T22:00:00Z'};
  const f = fixture(async () => response(200, item), {mode: 'detail'});
  await f.page.ready;
  const nodes = f.elements['orders-content'].children[0].children;
  const texts = nodes.map(node => node.textContent);
  assert.ok(texts.includes('维修中'));
  assert.ok(texts.includes('#2'));
  assert.ok(texts.includes('#3'));
  assert.ok(texts.includes('2026-11-19 05:00:00（北京时间）'));
  assert.ok(texts.includes('2026-11-19 06:00:00（北京时间）'));
  assert.ok(nodes.every(node => node.tag === 'dt' || node.tag === 'dd'));
});

test('401/403/404/503 retain safe error text; login only appears for available login and 401', async () => {
  for (const [status, login, hidden] of [[401,false,true],[401,true,false],[403,true,true],[404,true,true],[503,true,true]]) {
    const text = status === 404 ? '工单不存在或不可访问' : '<b>暂不可读取</b>';
    const f = fixture(async () => response(status, {error:'example', message:text}), {mode:'detail', login});
    await f.page.ready;
    assert.equal(f.elements['orders-message'].dataset.kind, 'error');
    assert.ok(f.elements['orders-message'].textContent.startsWith(text));
    assert.equal(f.elements['orders-login'].hidden, hidden);
    assert.equal(f.elements['orders-content'].children.length, 0);
  }
});

test('manual reload clears previously visible data when authorization is revoked', async () => {
  let calls = 0;
  const f = fixture(async () => ++calls === 1 ? summary() : response(403, {error:'forbidden', message:'读取权限已撤销'}));
  await f.page.ready;
  assert.equal(f.elements['orders-content'].children.length, 1);
  await f.reload();
  assert.equal(calls, 2);
  assert.equal(f.elements['orders-content'].children.length, 0);
  assert.equal(f.elements['orders-message'].textContent, '读取权限已撤销');
});

test('network or malformed responses show failure, never success/empty or automatic retry', async () => {
  for (const kind of ['network', 'json', 'invalid-list', 'invalid-detail']) {
    let calls = 0;
    const f = fixture(async () => {
      calls++;
      if (kind === 'network') throw new Error('disconnected');
      if (kind === 'json') return {ok: true, json: async () => {throw new Error('bad JSON');}};
      return response(200, kind === 'invalid-list' ? {items: [order()], total: 2} : {id: 41});
    }, {mode: kind === 'invalid-detail' ? 'detail' : 'list'});
    await f.page.ready;
    assert.equal(calls, 1);
    assert.equal(f.elements['orders-message'].dataset.kind, 'error');
    assert.match(f.elements['orders-message'].textContent, /手动重新加载/);
    assert.equal(f.elements['orders-content'].children.length, 0);
    assert.equal(f.elements['reload-orders'].disabled, false);
  }
});
