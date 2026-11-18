"use strict";
(() => {
  const { beijingTime } = typeof module !== "undefined" && module.exports ? require("./time.js") : window.M3Time;
  const categories = {ELECTRICAL: "电气故障", WATER: "给排水故障", FURNITURE: "家具故障", OTHER: "其他故障"};
  const states = {REPORTED: "已报修", ASSIGNED: "已派单", IN_REPAIR: "维修中"};
  const label = (map, key) => Object.prototype.hasOwnProperty.call(map, key) ? map[key] : "未知";
  const validId = value => Number.isSafeInteger(value) && value > 0;

  function mountDispatch(doc, fetcher) {
    const byId = id => doc.getElementById(id);
    const page = byId("dispatch-page"), message = byId("dispatch-message"), login = byId("dispatch-login");
    const status = byId("dispatch-status"), reload = byId("reload-dispatch"), content = byId("dispatch-content");
    const form = byId("assignment-form"), fields = byId("assignment-fields"), submit = byId("submit-assignment");
    const order = byId("dispatch-order"), target = byId("assigned-to"), detail = byId("assignment-detail");
    const queueMessage = byId("queue-message"), repairersMessage = byId("repairers-message");
    let items = [], people = [], loading = false, pending = false, uncertain = false, uncertainOrderId = null;
    let queueReady = false, peopleReady = false;
    const say = (text, kind = "info") => { message.textContent = text; message.dataset.kind = kind; };
    const element = (tag, text) => { const node = doc.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
    function sync() {
      fields.disabled = loading || pending || uncertain || !queueReady || !peopleReady || status.value !== "REPORTED" || !items.length || !people.length;
      submit.disabled = fields.disabled;
      reload.disabled = loading || pending;
      status.disabled = loading || pending;
      page.setAttribute("aria-busy", String(loading || pending));
    }
    function clearPrivate() {
      items = []; people = []; queueReady = peopleReady = false;
      content.replaceChildren(); order.replaceChildren(); target.replaceChildren();
      queueMessage.textContent = ""; repairersMessage.textContent = "";
      detail.hidden = true; detail.removeAttribute("href");
    }
    function showError(response, data) {
      if ([401, 403, 503].includes(response.status)) clearPrivate();
      say(typeof data?.message === "string" ? data.message : "派单服务暂不可用，请手动刷新。", "error");
      login.hidden = !(response.status === 401 && page.dataset.loginAvailable === "true");
      if (response.status === 401 && login.hidden) say(`${message.textContent}。登录入口尚未接入。`, "error");
    }
    function options(select, values, placeholder, describe) {
      select.replaceChildren();
      const blank = element("option", placeholder); blank.value = ""; select.append(blank);
      for (const value of values) { const node = element("option", describe(value)); node.value = String(value.id); select.append(node); }
    }
    function render() {
      content.replaceChildren();
      const list = element("ul"); list.className = "order-list";
      for (const item of items) {
        const row = element("li");
        row.append(element("h3", `#${item.id} · ${item.room_name}`));
        row.append(element("p", `${label(categories, item.fault_type)} · ${label(states, item.status)}`));
        row.append(element("p", `创建：${beijingTime(item.created_at)}`));
        if (item.assigned_at != null) row.append(element("p", `派单：${beijingTime(item.assigned_at)} · 受理人 #${item.assigned_to}`));
        const link = element("a", "查看详情"); link.href = `/m3/orders/${item.id}`; row.append(link); list.append(row);
      }
      content.append(list);
      queueMessage.textContent = items.length ? `共 ${items.length} 条${label(states, status.value)}工单。` : "当前状态暂无工单。";
      options(order, items.filter(item => item.status === "REPORTED"), "请选择待派工单", item => `#${item.id} · ${item.room_name}`);
      options(target, people, "请选择维修人员", person => `${person.display_name}（#${person.id}）`);
      repairersMessage.textContent = people.length ? `当前有 ${people.length} 名合法维修人员；提交时会重新核验资格。` : "暂无合法维修人员，暂不可派单。";
    }
    async function read(url) {
      const response = await fetcher(url, {credentials: "same-origin", cache: "no-store"});
      const data = await response.json();
      return {response, data};
    }
    async function load(kind = "all", keepMessage = false) {
      if (loading || (pending && !keepMessage)) return;
      loading = true; login.hidden = true;
      if (kind === "all") clearPrivate();
      else if (kind === "queue") { items = []; queueReady = false; content.replaceChildren(); order.replaceChildren(); }
      else { people = []; peopleReady = false; target.replaceChildren(); }
      if (!keepMessage) say("正在加载管理队列与维修人员…");
      sync();
      try {
        // 一次加载全部成功后才发布数据；任一鉴权失败不会被另一个迟到响应重新填回。
        const results = await Promise.all([
          kind !== "people" ? read(`/m3/work-orders/dispatch?status=${encodeURIComponent(status.value)}`) : null,
          kind !== "queue" ? read("/m3/repairers") : null,
        ]);
        const failure = results.find(result => result && !result.response.ok);
        if (failure) { showError(failure.response, failure.data); return; }
        if (results[0]) {
          const data = results[0].data;
          if (!Array.isArray(data?.items) || data.total !== data.items.length || !data.items.every(item => validId(item.id) && typeof item.room_name === "string" && item.status === status.value)) throw new Error("Invalid queue");
          items = data.items; queueReady = true;
        }
        if (results[1]) {
          const data = results[1].data;
          if (!Array.isArray(data?.items) || !data.items.every(item => validId(item.id) && typeof item.display_name === "string")) throw new Error("Invalid candidates");
          people = data.items; peopleReady = true;
        }
        render();
        if (uncertain && queueReady && peopleReady) { detail.href = `/m3/orders/${uncertainOrderId}`; detail.hidden = false; }
        if (!keepMessage) say(uncertain ? "上次派单结果仍需打开详情人工核对，本页不会重复提交。" : "管理数据已加载。", uncertain ? "error" : "success");
      } catch (_) {
        clearPrivate(); say("无法加载管理数据，请检查网络后手动刷新。", "error");
      } finally { loading = false; sync(); }
    }
    function unknownResult(orderId) {
      uncertain = true;
      uncertainOrderId = orderId;
      detail.href = `/m3/orders/${orderId}`; detail.hidden = false;
      say("派单结果不明，可能已提交。请打开该工单详情刷新核实；本页不会自动重发，也不会直接认定成功或失败。", "error");
    }
    async function send(event) {
      event.preventDefault();
      if (pending || loading || fields.disabled || uncertain) return;
      const orderId = Number(order.value), targetId = Number(target.value);
      if (!validId(orderId) || !validId(targetId) || !items.some(item => item.id === orderId && item.status === "REPORTED") || !people.some(person => person.id === targetId)) {
        say("请选择当前待派工单和维修人员。", "error"); return;
      }
      pending = true; detail.hidden = true; sync(); say("正在提交派单，请勿重复操作…");
      try {
        const response = await fetcher(`/m3/work-orders/${orderId}/assign`, {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify({assigned_to:targetId})});
        const data = await response.json();
        if (response.status === 200 && data?.id === orderId && data.status === "ASSIGNED" && data.assigned_to === targetId && typeof data.assigned_at === "string") {
          say(`工单 #${orderId} 派单成功，状态为已派单。`, "success");
          await load("queue", true);
          // 授权失效时 load 会清除所有数据，不再重新显示旧的详情入口。
          if (queueReady) { detail.href = `/m3/orders/${orderId}`; detail.hidden = false; }
        } else if (!response.ok && typeof data?.error === "string" && typeof data.message === "string" && response.status < 500) {
          showError(response, data);
          if (response.status === 409) {
            say("工单状态已变化，请核对刷新后的队列及详情。", "error"); await load("queue", true);
            if (queueReady) { detail.href = `/m3/orders/${orderId}`; detail.hidden = false; }
          }
          else if (response.status === 422) await load("people", true);
        } else if (response.status === 503 && data?.error === "database_busy") {
          showError(response, data); // 明确回滚；允许手动重新加载，不自动重发。
        } else if (response.status === 503 && ["auth_unavailable","schema_unavailable","storage_unavailable","dependency_unavailable"].includes(data?.error)) {
          showError(response, data);
        } else { unknownResult(orderId); }
      } catch (_) { unknownResult(orderId); }
      finally { pending = false; sync(); }
    }
    reload.addEventListener("click", () => load());
    status.addEventListener("change", () => load());
    form.addEventListener("submit", send);
    return {ready: load()};
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {mountDispatch};
  else mountDispatch(document, window.fetch.bind(window));
})();
