"use strict";
(() => {
  const categories = { ELECTRICAL: "电气故障", WATER: "给排水故障", FURNITURE: "家具故障", OTHER: "其他故障" };
  const statuses = { REPORTED: "已报修", ASSIGNED: "已派单", IN_REPAIR: "维修中" };
  const label = (mapping, value, fallback) => Object.prototype.hasOwnProperty.call(mapping, value) ? mapping[value] : fallback;
  const { beijingTime } = typeof module !== "undefined" && module.exports ? require("./time.js") : window.M3Time;
  const validSummary = item => item && Number.isSafeInteger(item.id) && item.id > 0 && typeof item.room_name === "string";

  function mountOrders(doc, fetcher) {
    const page = doc.getElementById("orders-page"), content = doc.getElementById("orders-content");
    const message = doc.getElementById("orders-message"), reload = doc.getElementById("reload-orders"), login = doc.getElementById("orders-login");
    let loading = false;
    const element = (tag, text) => { const node = doc.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
    const say = (text, kind = "info") => { message.textContent = text; message.dataset.kind = kind; };
    function renderList(data) {
      if (!Array.isArray(data.items) || data.total !== data.items.length || !data.items.every(validSummary)) throw new Error("Invalid list response");
      if (data.total === 0) { say("暂无本人的报修工单。", "empty"); return; }
      const list = element("ul");
      list.className = "order-list";
      for (const item of data.items) {
        const row = element("li");
        row.append(element("h2", item.room_name));
        row.append(element("p", `${label(categories, item.fault_type, "未知分类")} · ${label(statuses, item.status, "未知状态")}`));
        row.append(element("p", `创建时间：${beijingTime(item.created_at)}`));
        const link = element("a", `查看工单 #${item.id}`);
        link.href = `/m3/orders/${item.id}`;
        row.append(link);
        list.append(row);
      }
      content.append(list);
      say(`已加载 ${data.total} 条本人工单。`, "success");
    }
    function renderDetail(item) {
      if (!validSummary(item) || typeof item.description !== "string") throw new Error("Invalid detail response");
      const details = element("dl");
      function field(name, value, className = "") {
        const entry = element("dd", value);
        entry.className = className;
        details.append(element("dt", name), entry);
      }
      field("工单编号", `#${item.id}`);
      field("房间", item.room_name);
      field("故障分类", label(categories, item.fault_type, "未知分类"));
      field("当前状态", label(statuses, item.status, "未知状态"));
      field("故障描述", item.description, "order-description");
      field("报修人编号", `#${item.reporter_id}`);
      field("受理人编号", item.assigned_to == null ? "尚未派单" : `#${item.assigned_to}`);
      field("派单人编号", item.assigned_by == null ? "尚未派单" : `#${item.assigned_by}`);
      field("创建时间", beijingTime(item.created_at));
      field("更新时间", beijingTime(item.updated_at));
      field("派单时间", item.assigned_at == null ? "尚未派单" : beijingTime(item.assigned_at));
      field("开始维修", item.started_at == null ? "尚未开始维修" : beijingTime(item.started_at));
      content.append(details);
      say("工单详情已加载。", "success");
    }
    async function load() {
      if (loading) return;
      loading = true;
      reload.disabled = true;
      page.setAttribute("aria-busy", "true");
      login.hidden = true;
      content.replaceChildren(); // 重新授权失败时不保留上一次的工单正文。
      say("正在加载工单…");
      try {
        const url = page.dataset.mode === "detail" ? `/m3/work-orders/${encodeURIComponent(page.dataset.orderId)}` : "/m3/work-orders";
        const response = await fetcher(url, { credentials: "same-origin", cache: "no-store" });
        const data = await response.json();
        if (!response.ok) {
          say(typeof data.message === "string" ? data.message : "工单读取失败，请稍后重试。", "error");
          login.hidden = !(response.status === 401 && page.dataset.loginAvailable === "true");
          if (response.status === 401 && login.hidden) say(`${message.textContent}。登录入口尚未接入。`, "error");
          return;
        }
        if (page.dataset.mode === "detail") renderDetail(data); else renderList(data);
      } catch (_) {
        content.replaceChildren();
        say("无法读取工单，请检查网络或稍后手动重新加载。", "error");
      } finally {
        loading = false;
        reload.disabled = false;
        page.setAttribute("aria-busy", "false");
      }
    }
    reload.addEventListener("click", load);
    return { ready: load() };
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { beijingTime, mountOrders };
  else mountOrders(document, window.fetch.bind(window));
})();
