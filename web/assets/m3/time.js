"use strict";
(() => {
  const clock = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  });
  function beijingTime(value) {
    if (value == null) return "未记录";
    if (typeof value !== "string" || !value.endsWith("Z")) return "时间不可用";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "时间不可用";
    const parts = Object.fromEntries(clock.formatToParts(date).map(part => [part.type, part.value]));
    return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}（北京时间）`;
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { beijingTime };
  else window.M3Time = { beijingTime };
})();
