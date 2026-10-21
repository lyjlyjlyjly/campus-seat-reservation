/* G2 页面脚本：只通过公开 JSON 接口读写，不直接拼 SQL、不依赖任何前端框架。 */
(function () {
  "use strict";

  var STATUS_TEXT = {
    PENDING_L1: "待一级审批",
    PENDING_L2: "待二级审批",
    APPROVED: "已通过",
    REJECTED: "已驳回",
    REVOKED: "已撤销",
    CANCELLED: "已取消"
  };

  function feedback(element, message, kind) {
    if (!element) return;
    element.textContent = message;
    element.dataset.kind = kind || "";
  }

  function request(method, path, body) {
    var options = { method: method, headers: { Accept: "application/json" }, credentials: "same-origin" };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(path, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (payload) {
        if (!response.ok) {
          var error = new Error(payload.message || "请求失败（" + response.status + "）");
          error.status = response.status;
          error.code = payload.error || "";
          throw error;
        }
        return payload;
      });
    });
  }

  function describe(item) {
    return item.room.name + " · " + item.start_at.slice(11, 16) + "–" + item.end_at.slice(11, 16) +
      " (UTC) · " + (STATUS_TEXT[item.status] || item.status);
  }

  function badge(status) {
    var span = document.createElement("span");
    span.className = "badge";
    span.dataset.status = status;
    span.textContent = STATUS_TEXT[status] || status;
    return span;
  }

  function cell(row, text) {
    var td = document.createElement("td");
    td.textContent = text;
    row.appendChild(td);
    return td;
  }

  function localTime(item) {
    // 库里是 UTC，页面按浏览器本地时区显示，避免学生看错时间。
    var start = new Date(item.start_at).toLocaleString("zh-CN", { hour12: false });
    var end = new Date(item.end_at).toLocaleTimeString("zh-CN", { hour12: false });
    return start + " – " + end;
  }

  /* ---------- 登录页 ---------- */

  function initLogin() {
    var form = document.getElementById("login-form");
    var note = document.getElementById("login-feedback");
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var data = new FormData(form);
      feedback(note, "正在登录…", "warn");
      request("POST", "/m2/auth/login", {
        username: data.get("username"),
        password: data.get("password")
      }).then(function (identity) {
        var target = identity.permissions.indexOf("room:approve") >= 0 ? "/m2/approve" : "/m2/apply";
        feedback(note, "登录成功，正在跳转…", "ok");
        window.location.assign(target);
      }).catch(function (error) {
        feedback(note, error.message, "bad");
      });
    });
  }

  /* ---------- 申请页 ---------- */

  function initApply() {
    var form = document.getElementById("apply-form");
    var note = document.getElementById("apply-feedback");
    var select = document.getElementById("room-select");
    var table = document.querySelector("#mine-table tbody");

    request("GET", "/m2/rooms").then(function (payload) {
      payload.items.forEach(function (room) {
        var option = document.createElement("option");
        option.value = String(room.id);
        option.textContent = room.name + "（容量 " + room.capacity + " 人）";
        select.appendChild(option);
      });
    }).catch(function (error) {
      feedback(note, "教室列表加载失败：" + error.message, "bad");
    });

    function loadMine() {
      request("GET", "/m2/applications").then(function (payload) {
        table.innerHTML = "";
        if (!payload.items.length) {
          var empty = document.createElement("tr");
          var td = document.createElement("td");
          td.colSpan = 5;
          td.className = "hint";
          td.textContent = "还没有申请记录。";
          empty.appendChild(td);
          table.appendChild(empty);
          return;
        }
        payload.items.forEach(function (item) {
          var row = document.createElement("tr");
          cell(row, item.room.name);
          cell(row, localTime(item));
          cell(row, item.purpose);
          var statusCell = cell(row, "");
          statusCell.appendChild(badge(item.status));
          cell(row, item.decision_note || "—");
          table.appendChild(row);
        });
      }).catch(function (error) {
        feedback(note, "我的申请加载失败：" + error.message, "bad");
      });
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var date = data.get("date");
      var hour = String(data.get("hour")).padStart(2, "0");
      var hours = Number(data.get("hours"));
      // 页面按 +08:00 提交，后端统一换算成 UTC 存储。
      var start = new Date(date + "T" + hour + ":00:00+08:00");
      var end = new Date(start.getTime() + hours * 3600 * 1000);
      function iso(moment) {
        return moment.toISOString().replace(/\.\d{3}Z$/, "Z");
      }
      feedback(note, "正在提交…", "warn");
      request("POST", "/m2/applications", {
        room_id: Number(data.get("room")),
        start_at: iso(start),
        end_at: iso(end),
        purpose: String(data.get("purpose") || "").trim(),
        attendee_count: Number(data.get("attendees"))
      }).then(function (item) {
        feedback(note, "已提交，等待审批（" + describe(item) + "）", "ok");
        form.reset();
        loadMine();
      }).catch(function (error) {
        feedback(note, error.message, "bad");
      });
    });

    loadMine();
  }

  /* ---------- 审批页 ---------- */

  function initApprove() {
    var note = document.getElementById("approve-feedback");
    var table = document.querySelector("#pending-table tbody");

    function decide(item, approved) {
      var body = {};
      if (!approved) {
        var reason = window.prompt("请输入驳回理由（申请人可见）");
        if (!reason) {
          feedback(note, "已取消：驳回必须填写理由。", "warn");
          return;
        }
        body.note = reason;
      }
      var action = approved ? "approve" : "reject";
      feedback(note, "正在提交审批…", "warn");
      request("POST", "/m2/applications/" + item.id + "/" + action, body).then(function (updated) {
        feedback(note, "已" + (approved ? "通过" : "驳回") + "：" + describe(updated), "ok");
        load();
      }).catch(function (error) {
        feedback(note, error.message, "bad");
      });
    }

    function load() {
      request("GET", "/m2/applications/pending").then(function (payload) {
        table.innerHTML = "";
        if (!payload.items.length) {
          var empty = document.createElement("tr");
          var td = document.createElement("td");
          td.colSpan = 6;
          td.className = "hint";
          td.textContent = "没有待审批的申请。";
          empty.appendChild(td);
          table.appendChild(empty);
          return;
        }
        payload.items.forEach(function (item) {
          var row = document.createElement("tr");
          cell(row, item.applicant.display_name);
          cell(row, item.room.name);
          cell(row, localTime(item));
          cell(row, item.purpose + "（" + item.attendee_count + " 人）");
          var actions = document.createElement("td");
          var pass = document.createElement("button");
          pass.textContent = "通过";
          pass.addEventListener("click", function () { decide(item, true); });
          var reject = document.createElement("button");
          reject.textContent = "驳回";
          reject.className = "danger";
          reject.style.marginLeft = ".4rem";
          reject.addEventListener("click", function () { decide(item, false); });
          actions.appendChild(pass);
          actions.appendChild(reject);
          row.appendChild(actions);
          table.appendChild(row);
        });
      }).catch(function (error) {
        if (error.status === 403) {
          feedback(note, "当前账号没有审批权限（缺少 room:approve）。", "bad");
        } else {
          feedback(note, "待审列表加载失败：" + error.message, "bad");
        }
      });
    }

    document.getElementById("refresh").addEventListener("click", load);
    load();
  }

  /* ---------- 按页面分发 ---------- */

  document.addEventListener("DOMContentLoaded", function () {
    var page = document.body.dataset.page;
    if (page === "login") initLogin();
    if (page === "apply") initApply();
    if (page === "approve") initApprove();
  });
})();
