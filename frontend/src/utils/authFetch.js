// authFetch.js：封装原生 fetch，自动携带 Ac-Token 请求头；
// 收到 HTTP 401 时清理登录态并跳转登录页（行为与 request.js 的 handleUnauthorized 保持一致：
// 清理全部 key，且门户/登录/注册等公开页面仅静默清理、不强制跳转，避免“返回首页被弹回登录页”）
import { API_BASE } from './config.js'
import Router from '../router'

function handleUnauthorized() {
  localStorage.clear()
  const publicPaths = ['/portal', '/login', '/register']
  if (!publicPaths.includes(Router.currentRoute.value.path)) {
    Router.push('/login')
  }
}

// path 为以 / 开头的后端路径，options 与原生 fetch 的第二个参数一致
export async function authFetch(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = { ...(options.headers || {}) }
  if (token) {
    headers['Ac-Token'] = token
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    handleUnauthorized()
  }
  return res
}
