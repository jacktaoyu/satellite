// 告警中心共享 Store：跨页面聚合实时告警（卫星网络页 / 告警中心页共用）
// 数据来源：后端 GET /satellites/alerts（落 occ.alert_log）+ 前端运行期本地告警合并
import { reactive, readonly } from 'vue';

const state = reactive({
  alerts: [],          // { time, level, category, message, acknowledged, _local? }
  loaded: false,       // 是否已从后端拉取过
});

let pollTimer = null;

// 本地追加一条告警（前端产生的即时事件，如低电量），并尝试同步到后端日志
export function pushLocalAlert(level, category, message) {
  state.alerts.push({
    time: new Date().toLocaleString('sv-SE').replace('T', ' '),
    level, category, message, acknowledged: false, _local: true,
  });
  if (state.alerts.length > 200) state.alerts.splice(0, state.alerts.length - 200);
}

// 从后端拉取告警并合并（本地 _local 条目保留在前）
export async function fetchAlerts(authFetch) {
  try {
    const r = await authFetch('/satellites/alerts');
    const d = await r.json();
    const remote = Array.isArray(d.alerts) ? d.alerts : [];
    const locals = state.alerts.filter(a => a._local);
    state.alerts = [...locals, ...remote];
    state.loaded = true;
  } catch (e) { /* 后端未就绪时静默 */ }
}

// 启动轮询（5s），页面卸载时由调用方 stopAlertPoll
export function startAlertPoll(authFetch) {
  if (pollTimer) return;
  fetchAlerts(authFetch);
  pollTimer = setInterval(() => { if (!document.hidden) fetchAlerts(authFetch); }, 5000);
}
export function stopAlertPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

// 确认告警：index=-1 全部确认（仅后端条目；本地条目直接置位）
export async function ackAlert(authFetch, index) {
  try {
    await authFetch('/satellites/alerts/ack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index }),
    });
    if (index === -1) state.alerts.forEach(a => { a.acknowledged = true; });
  } catch (e) { }
}

export function useAlertStore() {
  return readonly(state);
}
export function useAlertStoreMutable() {
  return state;
}
