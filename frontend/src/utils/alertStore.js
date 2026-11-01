// 告警中心共享 Store：跨页面聚合实时告警（卫星网络页 / 告警中心页共用）
// 数据来源：后端 GET /satellites/alerts（落 occ.alert_log）+ 前端运行期本地告警合并
import { reactive, readonly } from 'vue';

const state = reactive({
  alerts: [],          // { id?, time, level, category, message, acknowledged, _local? }
  loaded: false,       // 是否已从后端拉取过
});

let pollTimer = null;
let fetchPromise = null;

// 本地追加一条告警（仅当前浏览器会话有效，后端告警由 OCC 统一记录）
export function pushLocalAlert(level, category, message) {
  state.alerts.push({
    time: new Date().toLocaleString('sv-SE').replace('T', ' '),
    level, category, message, acknowledged: false, _local: true,
  });
  if (state.alerts.length > 200) state.alerts.splice(0, state.alerts.length - 200);
}

// 从后端拉取告警并合并；并发调用共享同一个请求，避免慢请求与轮询重叠
export function fetchAlerts(authFetch) {
  if (fetchPromise) return fetchPromise;
  fetchPromise = (async () => {
    try {
      const r = await authFetch('/satellites/alerts');
      if (!r.ok) return false;
      const d = await r.json();
      const remote = Array.isArray(d.alerts) ? d.alerts : [];
      const locals = state.alerts.filter(a => a._local);
      state.alerts = [...locals, ...remote];
      state.loaded = true;
      return true;
    } catch (e) {
      return false;
    } finally {
      fetchPromise = null;
    }
  })();
  return fetchPromise;
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

// 按稳定 ID 确认告警；all=true 确认全部后端条目。仅在请求成功后更新共享状态
export async function ackAlert(authFetch, { id = null, all = false } = {}) {
  try {
    const r = await authFetch('/satellites/alerts/ack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(all ? { all: true } : { id }),
    });
    if (!r.ok) return false;
    if (all) state.alerts.forEach(a => { a.acknowledged = true; });
    return true;
  } catch (e) {
    return false;
  }
}

export function useAlertStore() {
  return readonly(state);
}

export function useAlertStoreMutable() {
  return state;
}
