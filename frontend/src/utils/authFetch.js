// authFetch.js：封装原生 fetch，自动携带 Ac-Token 请求头；
// 收到 HTTP 401 时清理登录态并跳转登录页（清理的 key 与 request.js 的 handleUnauthorized 保持一致）
import { API_BASE } from './config.js'
import Router from '../router'

function clearLoginState() {
  localStorage.removeItem('token')
  localStorage.removeItem('isAdmin')
  localStorage.removeItem('userInfo')
  localStorage.removeItem('userInfoid')
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
    clearLoginState()
    Router.push('/login')
  }
  return res
}
