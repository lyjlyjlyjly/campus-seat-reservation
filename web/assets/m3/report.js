/* 原生页面控制；Unicode 空白集合与 Python 3.10 str.strip 一致。 */
"use strict";
(() => {
  const spaces = "\\u0009-\\u000d\\u001c-\\u0020\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000";
  const edges = new RegExp(`^[${spaces}]+|[${spaces}]+$`, "gu");
  const normalize = value => value.replace(edges, "");
  const characterCount = value => Array.from(normalize(value)).length;

  function mountReport(doc, fetcher) {
    const byId = id => doc.getElementById(id);
    const form = byId("report-form"), fields = byId("report-fields");
    const room = byId("room-id"), category = byId("fault-type"), description = byId("description");
    const count = byId("description-count"), submit = byId("submit-report");
    const reload = byId("reload-rooms"), login = byId("report-login"), message = byId("report-message");
    let ready = false, pending = false, uncertain = false, completed = false;
    const say = (text, kind = "error") => { message.textContent = text; message.dataset.kind = kind; };
    const sync = () => {
      fields.disabled = !ready || pending || uncertain || completed;
      submit.disabled = fields.disabled;
      reload.disabled = pending || uncertain || completed;
      form.setAttribute("aria-busy", String(pending));
      submit.textContent = pending ? "正在提交…" : completed ? "已提交" : "提交报修";
    };
    function updateCount() {
      const length = characterCount(description.value);
      count.textContent = `${length} / 1000 字符（去除首尾空白后）`;
      const invalid = length < 1 || length > 1000 || description.value.includes("\u0000");
      count.dataset.invalid = String(invalid);
      description.setCustomValidity(invalid ? "请输入 1–1000 个 Unicode 字符，不含 U+0000。" : "");
    }
    function showError(response, data) {
      say(data.message);
      login.hidden = !(response.status === 401 && form.dataset.loginAvailable === "true");
      if (response.status === 401 && login.hidden) {
        say(`${data.message}。登录入口尚未接入，当前暂不可提交。`);
      }
    }
    async function loadRooms() {
      if (pending || uncertain || completed) return;
      ready = false;
      login.hidden = true;
      sync();
      reload.disabled = true;
      say("正在加载可报修房间…", "info");
      try {
        const response = await fetcher("/m3/rooms", { credentials: "same-origin", cache: "no-store" });
        const data = await response.json();
        if (!response.ok) {
          showError(response, { message: typeof data.message === "string" ? data.message : "房间加载失败，当前暂不可提交。" });
          return;
        }
        if (!Array.isArray(data.items)) throw new Error("Invalid room response");
        room.replaceChildren();
        const placeholder = doc.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "请选择房间";
        room.append(placeholder);
        for (const item of data.items) {
          const option = doc.createElement("option");
          option.value = String(item.id);
          option.textContent = `${item.name}${item.is_active === 0 ? "（停借，仍可报修）" : ""}`;
          room.append(option);
        }
        ready = data.items.length > 0;
        say(ready ? "房间已加载，请填写报修信息。" : "暂无可报修房间，当前暂不可提交。", "info");
      } catch (_) {
        say("无法加载房间，请检查网络后手动重新加载。当前暂不可提交。");
      } finally { sync(); }
    }
    function unknownResult() {
      uncertain = true;
      say("提交结果不明，工单可能已经生成。输入已保留；请联系工作人员核实，请勿刷新后重复提交。本接口不保证重复请求只创建一次。");
    }
    async function send(event) {
      event.preventDefault();
      if (!ready || pending || uncertain || completed) return;
      updateCount();
      if (!form.reportValidity()) return;
      const roomId = Number(room.value);
      if (!Number.isSafeInteger(roomId) || roomId <= 0) { say("请选择有效房间。"); return; }
      pending = true;
      login.hidden = true;
      sync();
      say("正在提交报修，请勿重复操作…", "info");
      try {
        const response = await fetcher("/m3/work-orders", {
          method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ room_id: roomId, fault_type: category.value, description: description.value }),
        });
        const data = await response.json();
        if (response.status === 201 && Number.isSafeInteger(data.id) && data.status === "REPORTED" && typeof data.created_at === "string") {
          completed = true;
          say(`报修成功！工单编号 #${data.id}，状态 REPORTED（已报修）。创建时间：${data.created_at}`, "success");
        } else if (!response.ok && typeof data.error === "string" && typeof data.message === "string" && response.status < 500) {
          showError(response, data);
          if (response.status === 401 || response.status === 403) ready = false;
        } else if (response.status === 503 && ["database_busy", "auth_unavailable", "storage_unavailable", "schema_unavailable", "dependency_unavailable"].includes(data.error)) {
          showError(response, data);
          if (data.error !== "database_busy") ready = false;
        } else { unknownResult(); }
      } catch (_) { unknownResult(); }
      finally { pending = false; sync(); }
    }
    description.addEventListener("input", updateCount);
    form.addEventListener("submit", send);
    reload.addEventListener("click", loadRooms);
    updateCount();
    sync();
    return { ready: loadRooms() };
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { normalize, characterCount, mountReport };
  } else { mountReport(document, window.fetch.bind(window)); }
})();
