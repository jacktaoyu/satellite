// 全局后端 API 地址配置（统一收敛，避免各页面硬编码 localhost/127.0.0.1）
// 注意：localhost 与 127.0.0.1 属于不同源，必须与 request.js 的 baseURL 保持一致
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5001';
