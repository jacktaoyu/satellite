// 后端统一使用不带时区的 UTC 字符串（如 "2025-06-06 08:02:55"）。
// 展示层按浏览器本地时区格式化，内部时间轴则使用同一时间解析约定生成 UTC 时间戳。
function parseUtcDate(utcStr) {
  if (!utcStr) return null;
  const iso = String(utcStr).trim().replace(' ', 'T');
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return Number.isNaN(d.getTime()) ? null : d;
}

export function utcToTimestamp(utcStr) {
  const d = parseUtcDate(utcStr);
  return d ? d.getTime() : NaN;
}

export function utcToLocalString(utcStr) {
  if (!utcStr) return '--';
  const d = parseUtcDate(utcStr);
  if (!d) return String(utcStr).slice(0, 19);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
