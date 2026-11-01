// authFetch.js：封装原生 fetch，自动携带 Ac-Token、超时取消和外部 AbortSignal。
import { API_BASE } from './config.js'
import Router from '../router'

const LOGIN_STORAGE_KEYS = ['token', 'isAdmin', 'userInfo', 'userInfoid', 'nickname']

function clearLoginState() {
  LOGIN_STORAGE_KEYS.forEach(key => localStorage.removeItem(key))
}

function handleUnauthorized() {
  clearLoginState()
  const publicPaths = ['/portal', '/login', '/register']
  if (!publicPaths.includes(Router.currentRoute.value.path)) {
    Router.push('/login')
  }
}

// path 为以 / 开头的后端路径；options 额外支持 timeout（毫秒），其他字段与 fetch 一致
export async function authFetch(path, options = {}) {
  const { timeout = 15000, signal: externalSignal, ...fetchOptions } = options
  const token = localStorage.getItem('token')
  const headers = { ...(fetchOptions.headers || {}) }
  if (token) {
    headers['Ac-Token'] = token
  }

  const controller = new AbortController()
  const onExternalAbort = () => controller.abort()
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort()
    else externalSignal.addEventListener('abort', onExternalAbort, { once: true })
  }
  const timeoutId = timeout > 0 ? setTimeout(() => controller.abort(), timeout) : null

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    })
    if (res.status === 401) {
      handleUnauthorized()
    }
    return res
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
    if (externalSignal) externalSignal.removeEventListener('abort', onExternalAbort)
  }
}
