"use strict";
(() => {
  const {beijingTime} = typeof module !== "undefined" && module.exports ? require("./time.js") : window.M3Time;
  const categories = {ELECTRICAL:"电气故障", WATER:"给排水故障", FURNITURE:"家具故障", OTHER:"其他故障"};
  const states = {ASSIGNED:"已派单", IN_REPAIR:"维修中"};
  const label = (map, key) => Object.prototype.hasOwnProperty.call(map,key) ? map[key] : "未知";
  const validId = id => Number.isSafeInteger(id) && id > 0;

  function mountAssigned(doc, fetcher) {
    const get = id => doc.getElementById(id);
    const page=get("assigned-page"), message=get("assigned-message"), login=get("assigned-login");
    const status=get("assigned-status"), reload=get("reload-assigned"), content=get("assigned-content");
    let items=[], buttons=[], loading=false, pending=false;
    const uncertain = new Set();
    const say = (text,kind="info") => { message.textContent=text; message.dataset.kind=kind; };
    const element = (tag,text) => { const node=doc.createElement(tag); if(text!==undefined) node.textContent=text; return node; };
    function sync() {
      reload.disabled=loading||pending; status.disabled=loading||pending;
      page.setAttribute("aria-busy",String(loading||pending));
      for(const [button,id] of buttons) button.disabled=loading||pending||uncertain.has(id);
    }
    function clearPrivate() { items=[]; buttons=[]; content.replaceChildren(); }
    function error(response,data) {
      if([401,403,503].includes(response.status)) clearPrivate();
      say(typeof data?.message==="string" ? data.message : "服务暂不可用，请重新查询。","error");
      login.hidden=!(response.status===401 && page.dataset.loginAvailable==="true");
      if(response.status===401 && login.hidden) say(message.textContent+"。登录入口尚未接入。","error");
    }
    function render() {
      content.replaceChildren(); buttons=[];
      if(!items.length) { content.append(element("p","当前筛选下暂无本人受理工单。")); sync(); return; }
      content.append(element("p",`共 ${items.length} 条本人受理工单。`));
      const list=element("ul"); list.className="order-list";
      for(const item of items) {
        const row=element("li");
        row.append(element("h2",`#${item.id} · ${item.room_name}`));
        row.append(element("p",`${label(categories,item.fault_type)} · ${label(states,item.status)}`));
        for(const [field,name] of [["created_at","创建"],["assigned_at","派单"],["started_at","开始"],["updated_at","更新"]])
          row.append(element("p",`${name}：${beijingTime(item[field])}`));
        const detail=element("a","查看详情"); detail.href=`/m3/orders/${item.id}`; row.append(detail);
        if(item.status==="ASSIGNED" && item.can_start) {
          const button=element("button",`开始维修 #${item.id}`); button.type="button";
          button.addEventListener("click",()=>start(item.id)); buttons.push([button,item.id]); row.append(button);
        }
        list.append(row);
      }
      content.append(list); sync();
    }
    async function load(keepMessage=false) {
      if(loading || (pending && !keepMessage)) return;
      loading=true; login.hidden=true; clearPrivate(); sync();
      if(!keepMessage) say("正在加载本人受理工单…");
      try {
        const url="/m3/work-orders/assigned"+(status.value ? `?status=${encodeURIComponent(status.value)}` : "");
        const response=await fetcher(url,{credentials:"same-origin",cache:"no-store"});
        const data=await response.json();
        if(!response.ok) { error(response,data); return; }
        if(!Array.isArray(data?.items) || data.total!==data.items.length || !data.items.every(item=>
          validId(item.id) && typeof item.room_name==="string" && typeof item.can_start==="boolean" &&
          ["ASSIGNED","IN_REPAIR"].includes(item.status) && (!status.value || item.status===status.value))) throw new Error("Invalid list");
        items=data.items; render();
        if(!keepMessage) say(uncertain.size ? "已重新查询，请根据当前状态核实上次操作；本页不会重复发送结果不明的请求。" : "本人受理工单已加载。");
      } catch(_) { clearPrivate(); say("无法加载工单，请检查网络后重新查询。","error"); }
      finally { loading=false; sync(); }
    }
    function unknown(id) {
      uncertain.add(id);
      say(`工单 #${id} 的开始结果不明，可能已提交。请重新查询核实；本页不会重发，也不认定成功或失败。`,"error");
    }
    async function start(id) {
      if(pending||loading||uncertain.has(id)||!items.some(item=>item.id===id && item.status==="ASSIGNED" && item.can_start)) return;
      pending=true; login.hidden=true; sync(); say(`正在开始维修 #${id}，请勿重复操作…`);
      try {
        const response=await fetcher(`/m3/work-orders/${id}/start`,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:"{}"});
        const data=await response.json();
        if(response.status===200 && data?.id===id && data.status==="IN_REPAIR" && typeof data.started_at==="string" && data.started_at===data.updated_at) {
          items=items.map(item=>item.id===id ? {...item,status:data.status,started_at:data.started_at,updated_at:data.updated_at,can_start:false} : item)
            .filter(item=>!status.value || item.status===status.value);
          render(); say(`工单 #${id} 已开始维修，开始时间：${beijingTime(data.started_at)}`,"success");
        } else if(!response.ok && response.status<500 && typeof data?.error==="string" && typeof data.message==="string") {
          error(response,data);
          if(response.status===409) { say("工单状态已变化，请核对重新查询的当前状态。","error"); await load(true); }
          else if(response.status===404) await load(true);
        } else if(response.status===503 && ["database_busy","auth_unavailable","schema_unavailable","storage_unavailable","dependency_unavailable"].includes(data?.error)) {
          error(response,data);
        } else unknown(id);
      } catch(_) { unknown(id); }
      finally { pending=false; sync(); }
    }
    reload.addEventListener("click",()=>load()); status.addEventListener("change",()=>load());
    return {ready:load()};
  }
  if(typeof module!=="undefined" && module.exports) module.exports={mountAssigned};
  else mountAssigned(document,window.fetch.bind(window));
})();
