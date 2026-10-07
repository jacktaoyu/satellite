// 仿真时间显示工具：后端统一以 UTC（naive 字符串，如 "2025-06-06 08:02:55"）存储与返回，
// 用户在系统设置页提交的时间是本地时间（入口已转 UTC），因此展示层需把 UTC 转回本地时区，
// 保证"设置什么时间就看到什么时间"，避免出现 8 小时偏差。
export function utcToLocalString(utcStr) {
  if (!utcStr) return '--';
  // 归一化为 ISO 并标注 Z（UTC），交给 Date 按浏览器本地时区解析
  const iso = String(utcStr).trim().replace(' ', 'T');
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  if (Number.isNaN(d.getTime())) return String(utcStr).slice(0, 19);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
