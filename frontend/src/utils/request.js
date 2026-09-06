import axios from 'axios'
import { ElMessage } from 'element-plus'
import Router from '../router'
import { API_BASE } from './config.js'
//request.js文件用来封装axios
let hostURL = API_BASE

// 创建axios实例
const request = axios.create({
  baseURL: hostURL,
  timeout: 15000,// 请求超时时间
})

// 401 统一处理：清除全部本地登录态并跳转登录页（与 main.vue 退出登录逻辑保持一致）
function handleUnauthorized() {
  localStorage.clear()
  Router.push("/login") //跳转到登陆页面
}

//响应拦截器
request.interceptors.response.use(res => {
  // 兼容后端返回的 code 格式
  if (!!res.data.code && res.data.code != 200) {
    if (res.data.code === 401) {
      handleUnauthorized()
    }
    ElMessage({
      showClose: true,
      message: res.data.message || "未知错误",
      type: 'warning',
    })
    return Promise.reject(res)
  }
  // 兼容后端返回的 meta.status 格式
  if (res.data.meta && res.data.meta.status && res.data.meta.status != 200) {
    if (res.data.meta.status === 401) {
      handleUnauthorized()
    }
    ElMessage({
      showClose: true,
      message: res.data.meta.message || "未知错误",
      type: 'warning',
    })
    return Promise.reject(res)
  }
  return res
}, error => {
  if (error.response?.status === 401) {
    handleUnauthorized()
  }
  const errorMessage =
    error.response?.data?.meta?.message ||
    error.response?.data?.error ||
    error.response?.data?.message ||
    error.message
  ElMessage({
    showClose: true,
    message: errorMessage || "内部错误",
    type: 'error',
  })
  return Promise.reject(error)
});

//请求拦截器
request.interceptors.request.use(config => {
  let token = localStorage.getItem("token");
  if (token) {
    config.headers['Ac-Token'] = token
  }
  return config
}, error => {
  return Promise.reject(error)
});

export default request
