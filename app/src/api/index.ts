/**
 * ============================================================
 * 智能星簇协同运行验证系统 —— 数据接入层（真实后端接入）
 * ------------------------------------------------------------
 * 对接 Flask 后端（http://127.0.0.1:5001），请求/响应结构以旧 Vue
 * 前端（frontend/src/views）的实际调用为准，在此层完成字段映射，
 * 页面组件按既有数据结构消费、无需改动。
 * ============================================================
 */

const BASE = 'http://127.0.0.1:5001'

export const getToken = () => localStorage.getItem('Ac-Token') ?? ''
export const clearToken = () => localStorage.removeItem('Ac-Token')

// ==================== 类型定义 ====================

export type SensorType = 'SAR' | '光学' | '红外'
export type TaskStatus = '等待执行' | '执行中' | '暂停' | '已完成'
export type TaskType = '点目标' | '区域目标' | '广域目标' | '移动目标' | '静态观测' | '周期观测'

export interface Satellite {
  id: number
  name: string
  orbit: string
  sensorType: SensorType
  battery: number
  storage: number
  resolution: number
  available: boolean
  lat: number
  lon: number
  altitude: number
  period: number
  pitch: number
  roll: number
  downlinkRate: number
  power: { idle: number; solar: number; maneuver: number; imaging: number }
  payload: {
    rotateSpeed: number
    stableTime: number
    maxRoll: number
    maxPitch: number
    cloudThreshold: number
    swath: number
  }
  linkedStations: string[]
  linkedGeo: string
  currentTask?: string
  taskCount: number
  laps: number
  speed: number
  /** TLE 两行根数（来自 getAllSatelliteInfo），供前端实时推算真实轨道 */
  tle1?: string
  tle2?: string
}

export interface Task {
  id: number
  name: string
  type: TaskType
  priority: number
  emergency: boolean
  sensorType: SensorType
  resolution: number
  satellite?: string
  cluster?: string
  mergedId?: number
  status: TaskStatus
  startTime: string
  endTime: string
  scheduledTime?: string
  region?: string
  /** 执行进度：后端无进度字段，已完成=100%、未开始=0%、执行中=未知（undefined，页面显示「—」） */
  progress?: number
  result?: '成功' | '失败'
}

export interface Cluster {
  id: number
  name: string
  orbits: string[]
  satelliteCount: number
  satellites: string[]
  payloadSpec: string
  available: boolean
}

export interface GroundStation {
  name: string
  location: [number, number] // [纬度, 经度]
  connecting_satellite: string[]
}

export interface Event {
  id: number
  time: string
  level: 'info' | 'warning' | 'alarm'
  content: string
}

export interface LoginParams { username: string; password: string; value: string }
export interface UserInfo { username: string; nickname: string; role: 'admin' | 'user' }

// ==================== 工具 ====================

const pad = (n: number) => String(n).padStart(2, '0')
export const fmtTime = (d: Date) =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`

// 最新仿真时间缓存（由 getCurrentTime 轮询更新，供事件流打时间戳）
let lastSimTime = ''

/** 统一请求帮手：自动携带 Ac-Token；401 清理登录态并跳登录页；非 2xx 抛出带 message 的错误 */
async function request(
  path: string,
  opts: { method?: string; body?: unknown; params?: Record<string, string | number>; formData?: FormData } = {},
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<any> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers['Ac-Token'] = token

  let url = `${BASE}${path}`
  if (opts.params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(opts.params)) qs.set(k, String(v))
    url += `?${qs.toString()}`
  }

  let body: BodyInit | undefined
  if (opts.formData) {
    body = opts.formData // 浏览器自动带 multipart boundary
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }

  const res = await fetch(url, { method: opts.method ?? (body ? 'POST' : 'GET'), headers, body })

  if (res.status === 401) {
    clearToken()
    localStorage.removeItem('userInfo')
    location.href = '/login'
    throw new Error('登录状态已失效，请重新登录')
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const j = await res.json()
      msg = j?.meta?.message || j?.message || j?.error || j?.msg || msg
    } catch { /* 非 JSON 错误响应 */ }
    throw new Error(msg)
  }
  const ct = res.headers.get('Content-Type') ?? ''
  if (ct.includes('application/json')) return res.json()
  return res.text()
}

/** 文件下载：fetch blob → objectURL → <a download> 触发浏览器下载（参考旧前端 downloadBlob 写法） */
async function downloadFile(
  path: string,
  opts: { method?: string; body?: unknown; fallbackName: string },
): Promise<{ code: number }> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers['Ac-Token'] = token
  let body: BodyInit | undefined
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const res = await fetch(`${BASE}${path}`, { method: opts.method ?? 'GET', headers, body })
  if (res.status === 401) {
    clearToken()
    localStorage.removeItem('userInfo')
    location.href = '/login'
    throw new Error('登录状态已失效，请重新登录')
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const j = await res.json()
      msg = j?.meta?.message || j?.message || j?.error || j?.msg || msg
    } catch { /* ignore */ }
    throw new Error(msg)
  }
  const blob = await res.blob()
  // 优先取 Content-Disposition 文件名（CORS 未暴露该头时退回默认名）
  let name = opts.fallbackName
  const cd = res.headers.get('Content-Disposition') ?? ''
  const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
  if (m) {
    try { name = decodeURIComponent(m[1]) } catch { name = m[1] }
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  return { code: 200 }
}

/** 操作类接口统一包装：成功 {code:200}，失败 {code:400,msg} 并打印日志（页面大多不处理 rejection） */
async function action(p: Promise<unknown>): Promise<{ code: number; msg?: string }> {
  try {
    await p
    return { code: 200 }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    console.error('[api] 操作失败:', msg)
    return { code: 400, msg }
  }
}

// ---------- 字段映射（与旧 Vue 前端保持一致） ----------

/** 载荷类型：后端英文键 → 页面中文枚举 */
const SENSOR_MAP: Record<string, SensorType> = { optical: '光学', SAR: 'SAR', infrared: '红外', 光学: '光学', 红外: '红外' }
const toSensor = (v: unknown): SensorType => SENSOR_MAP[String(v ?? '')] ?? '光学'
/** 页面中文枚举 → 后端英文键 */
const SENSOR_EN: Record<string, string> = { 光学: 'optical', SAR: 'SAR', 红外: 'infrared' }

/** 任务状态：后端 等待规划/正在执行/Success/Failed → 页面 等待执行/执行中/已完成 */
const STATUS_MAP: Record<string, TaskStatus> = {
  等待规划: '等待执行', 等待执行: '等待执行', 正在执行: '执行中', 执行中: '执行中',
  暂停: '暂停', 已完成: '已完成', Success: '已完成', Failed: '已完成',
}

/** 解析 "[x, y, z]" 形式的数组字符串 */
function parseVec(v: unknown): number[] {
  if (Array.isArray(v)) return v.map(Number).filter((n) => !isNaN(n))
  if (typeof v !== 'string') return []
  return v.replace(/[[\]]/g, '').split(',').map((s) => Number(s.trim())).filter((n) => !isNaN(n))
}

/** 由轨道高度（km）按开普勒第三定律估算轨道周期（min） */
const periodFromAltitude = (altKm: number) => {
  const a = 6371 + altKm
  return Math.round((2 * Math.PI * Math.sqrt(a ** 3 / 398600.4418)) / 60 * 10) / 10
}

/** 由 TLE 第二行平均运动（rev/day）计算轨道周期（min），失败返回 0 */
function periodFromTle(tle2: unknown): number {
  if (typeof tle2 !== 'string' || tle2.length < 63) return 0
  const mm = parseFloat(tle2.substring(52, 63))
  if (isNaN(mm) || mm <= 0) return 0
  return Math.round((1440 / mm) * 100) / 100
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapTask(t: any): Task {
  const rawStatus = String(t.status ?? '')
  const status = STATUS_MAP[rawStatus] ?? '等待执行'
  return {
    id: t.id,
    name: t.task_name ?? t.taskName ?? '',
    type: (t.type ?? t.taskType ?? '点目标') as TaskType,
    priority: t.priority ?? 0,
    emergency: Boolean(t.is_urgent ?? t.isEmergency),
    sensorType: toSensor(t.payload ?? t.sensorType),
    resolution: t.resolution ?? 0,
    satellite: t.satellite_name || t.assignedSatelliteName || undefined,
    cluster: t.cluster_name || t.clusterName || undefined,
    mergedId: t.friend_task ?? t.friendTask ?? undefined,
    status,
    startTime: String(t.start_time ?? t.startTime ?? '').slice(0, 19),
    endTime: String(t.end_time ?? t.endTime ?? '').slice(0, 19),
    region: t.coordinates ?? t.targetLocation ?? undefined,
    // 后端无进度字段：已完成=100%、未开始=0%、执行中=undefined（页面显示「—」，不再按 50% 造假）
    progress: status === '已完成' ? 100 : status === '执行中' ? undefined : 0,
    result: rawStatus === 'Success' ? '成功' : rawStatus === 'Failed' ? '失败' : undefined,
  }
}

/** getAllSatellites（简表） + getAllSatelliteInfo（详情）按名称合并为页面 Satellite 结构 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mergeSatellite(s: any, info: any): Satellite {
  // position 为 ECEF 坐标（km），换算经纬度与高度
  const pos = parseVec(info?.position)
  const r = pos.length === 3 ? Math.hypot(pos[0], pos[1], pos[2]) : 0
  const lat = r > 0 ? Math.round((Math.asin(pos[2] / r) * 180) / Math.PI * 100) / 100 : 0
  const lon = r > 0 ? Math.round((Math.atan2(pos[1], pos[0]) * 180) / Math.PI * 100) / 100 : 0
  const altitude = r > 0 ? Math.round(r - 6371) : 0
  const period = periodFromTle(info?.tle2) || periodFromAltitude(altitude)
  const speedVec = parseVec(info?.speed)
  return {
    id: s.id,
    name: s.name,
    orbit: String(s.orbit ?? ''), // 后端别名字符串，如「第10轨道第0卫星」
    sensorType: toSensor(s.loadType ?? info?.payload),
    battery: Math.round((s.battery ?? 0) * 100) / 100,
    storage: Math.round((s.storage ?? 0) * 100) / 100,
    resolution: s.resolution ?? info?.resolution ?? 0,
    // 批量接口已返回 is_available（真实启停状态），缺字段时默认可用
    available: Boolean(s.is_available ?? true),
    lat, lon, altitude, period,
    pitch: info?.pitchAngle ?? 0,
    roll: info?.rollAngle ?? 0,
    downlinkRate: 0,
    power: { idle: 0, solar: 0, maneuver: 0, imaging: 0 },
    payload: { rotateSpeed: 0, stableTime: 0, maxRoll: 0, maxPitch: 0, cloudThreshold: 0, swath: info?.width ?? 0 },
    linkedStations: info?.connecting_ground_station ? [info.connecting_ground_station] : [],
    linkedGeo: info?.connecting_geo ?? '无',
    currentTask: undefined,
    taskCount: 0,
    laps: 0,
    speed: speedVec.length === 3 ? Math.round(Math.hypot(speedVec[0], speedVec[1], speedVec[2]) * 100) / 100 : 0,
    tle1: info?.tle1 ?? undefined,
    tle2: info?.tle2 ?? undefined,
  }
}

/** getSatelliteById / getSatelliteByName 单星详情映射 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapSatDetail(d: any): Satellite {
  const pos = parseVec(d.position)
  const r = pos.length === 3 ? Math.hypot(pos[0], pos[1], pos[2]) : 0
  const sub = parseVec(d.sub_point) // 星下点 [纬度, 经度]
  const altitude = r > 0 ? Math.round(r - 6371) : 0
  const speedVec = parseVec(d.speed)
  const orbitRaw = d.orbit
  return {
    id: d.id,
    name: d.name,
    // getSatelliteById 返回别名字符串；getSatelliteByName 返回轨道编号
    orbit: typeof orbitRaw === 'number' ? `第${orbitRaw}轨道` : String(orbitRaw ?? ''),
    sensorType: toSensor(d.loadType),
    battery: Math.round((d.battery ?? 0) * 100) / 100,
    storage: Math.round((d.storage ?? 0) * 100) / 100,
    resolution: d.resolution ?? 0,
    available: Boolean(d.is_available ?? true),
    lat: sub[0] ?? 0,
    lon: sub[1] ?? 0,
    altitude,
    period: periodFromAltitude(altitude),
    pitch: d.pitchAngle ?? 0,
    roll: d.sideAngle ?? 0,
    downlinkRate: d.downlink_rate ?? 0,
    power: {
      idle: d.eclipse_powers ?? 0,
      solar: d.sunlight_powers ?? 0,
      maneuver: d.maneuver_powers ?? 0,
      imaging: d.imaging_powers ?? 0,
    },
    payload: {
      rotateSpeed: d.angleVelocity ?? d.angle_velocity ?? 0,
      stableTime: d.settlingTime ?? 0,
      maxRoll: d.side_swing_angle_Max ?? 0,
      maxPitch: d.pitch_angle_Max ?? 0,
      cloudThreshold: d.threshold ?? 0,
      swath: d.width ?? 0,
    },
    linkedStations: d.connecting_ground_station ? [d.connecting_ground_station] : [],
    linkedGeo: d.connecting_geo ?? '无',
    currentTask: d.running_task ?? undefined,
    taskCount: d.task_num ?? 0,
    laps: d.turns ?? 0,
    speed: speedVec.length === 3 ? Math.round(Math.hypot(speedVec[0], speedVec[1], speedVec[2]) * 100) / 100 : 0,
  }
}

// ==================== 鉴权 ====================

/** POST /login/ —— 登录（旧前端 value 传 '1'/'3'，页面传中文角色，此处转换） */
export async function login(p: LoginParams): Promise<{ code: number; data?: UserInfo; msg?: string }> {
  try {
    const res = await fetch(`${BASE}/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: p.username,
        password: p.password,
        value: p.value === '管理员' ? '1' : p.value === '用户' ? '3' : p.value,
      }),
    })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const j: any = await res.json().catch(() => ({}))
    if (res.ok && j?.meta?.status === 200 && j.data) {
      const d = j.data
      const info: UserInfo = {
        username: d.username,
        nickname: d.nickname || d.username,
        role: d.isAdmin === 1 ? 'admin' : 'user',
      }
      localStorage.setItem('Ac-Token', d.token)
      localStorage.setItem('userInfo', JSON.stringify(info))
      return { code: 200, data: info }
    }
    return { code: 400, msg: j?.meta?.message || j?.message || '账号或密码错误' }
  } catch {
    return { code: 400, msg: '无法连接后端服务' }
  }
}

/** POST /register/ —— 注册（后端强制普通用户 user_type='0'） */
export async function register(p: { username: string; password: string }): Promise<{ code: number; msg?: string }> {
  try {
    const res = await fetch(`${BASE}/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: p.username, password: p.password, value: '0' }),
    })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const j: any = await res.json().catch(() => ({}))
    if (res.ok && j?.meta?.status === 200) return { code: 200 }
    return { code: 400, msg: j?.meta?.message || j?.message || '注册失败' }
  } catch {
    return { code: 400, msg: '无法连接后端服务' }
  }
}

/** POST /updatePassword —— 修改密码（后端要求 confirmPassword，与 password 同值） */
export async function updatePassword(p: { username: string; password: string }): Promise<{ code: number; msg?: string }> {
  try {
    const j = await request('/updatePassword', {
      method: 'POST',
      body: { username: p.username, password: p.password, confirmPassword: p.password },
    })
    return { code: 200, msg: j?.message }
  } catch (e) {
    return { code: 400, msg: e instanceof Error ? e.message : '修改失败' }
  }
}

// ==================== 门户统计 ====================

/** GET /statistics（白名单接口，无需登录） */
export async function getStatistics() {
  try {
    const j = await request('/statistics')
    const d = j?.data ?? {}
    return {
      satellites: d.satellite_count ?? 0,
      todayTasks: d.today_task_count ?? 0,
      pendingTasks: d.pending_task_count ?? 0,
      clients: d.online_clients ?? 0,
    }
  } catch (e) {
    console.warn('[api] getStatistics 失败:', e)
    return { satellites: 0, todayTasks: 0, pendingTasks: 0, clients: 0 }
  }
}

// ==================== 卫星网络大屏 ====================

/** GET /getCurrentTime —— 真实仿真时钟 */
export async function getCurrentTime() {
  try {
    const j = await request('/getCurrentTime')
    lastSimTime = String(j?.current_time ?? '').slice(0, 19)
  } catch (e) {
    console.warn('[api] getCurrentTime 失败:', e)
  }
  return lastSimTime
}

/** POST /satellites/getAllSatellites + /satellites/getAllSatelliteInfo 合并（大屏/管理共用） */
export async function getAllSatellites(): Promise<Satellite[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list: any[] = await request('/satellites/getAllSatellites', { method: 'POST', body: { sate_name: '' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const info: any[] = await request('/satellites/getAllSatelliteInfo', { method: 'POST', body: {} }).catch(() => [])
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const infoMap = new Map<string, any>(Array.isArray(info) ? info.map((i) => [i.satName, i]) : [])
    return (Array.isArray(list) ? list : []).map((s) => mergeSatellite(s, infoMap.get(s.name)))
  } catch (e) {
    console.warn('[api] getAllSatellites 失败:', e)
    return []
  }
}

/** POST /satellites/getAllSatelliteInfo（大屏轮询详情）——与列表合并结果一致 */
export async function getAllSatelliteInfo(): Promise<Satellite[]> {
  return getAllSatellites()
}

/** GET /tasks/getNewTasksByCondition —— 全部未完成任务 */
export async function getTasksByCondition(): Promise<Task[]> {
  try {
    const j = await request('/tasks/getNewTasksByCondition')
    return (Array.isArray(j) ? j : []).map(mapTask)
  } catch (e) {
    console.warn('[api] getTasksByCondition 失败:', e)
    return []
  }
}

/** GET /getPlanningEvaluation —— 规划评估（满足率/耗时/趋势） + 任务状态统计 */
export async function getPlanningEvaluation() {
  const empty = { satisfactionRate: 0, planningTime: 0, trend: [] as { round: number; rate: number }[], taskStats: { waiting: 0, running: 0, done: 0 } }
  try {
    const [evRes, tasks, stats] = await Promise.all([
      request('/getPlanningEvaluation'),
      request('/tasks/getNewTasksByCondition').catch(() => []),
      request('/statistics').catch(() => null),
    ])
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const evaluation: any[] = evRes?.evaluation ?? []
    const latest = evaluation[evaluation.length - 1]
    const trend = evaluation.slice(-10).map((e, i) => ({
      round: i + 1,
      rate: Math.round((e.task_satisfaction || 0) * 100),
    }))
    const taskList = Array.isArray(tasks) ? tasks : []
    return {
      satisfactionRate: latest ? Math.round((latest.task_satisfaction || 0) * 100) : 0,
      planningTime: latest ? Math.round((latest.duration || 0) * 100) / 100 : 0,
      trend,
      taskStats: {
        waiting: taskList.filter((t) => t.status === '等待规划' || t.status === '等待执行').length,
        running: taskList.filter((t) => t.status === '正在执行' || t.status === '执行中').length,
        done: stats?.data?.completed_task_count ?? 0,
      },
    }
  } catch (e) {
    console.warn('[api] getPlanningEvaluation 失败:', e)
    return empty
  }
}

// ===== 实时事件流 =====
// TODO: 后端无事件接口，事件由轮询真实数据本地 diff 生成（参考旧 Satellite_network.vue 逻辑）
const prevTaskStatus: Record<string, string> = {}
const lowBatteryWarned = new Set<string>()
let lastSatisfaction: number | null = null
let eventSeq = 0

/** 实时事件流：任务状态 diff + 低电量告警 + 规划满足率变更 */
export async function getEvents(): Promise<Event[]> {
  const events: Event[] = []
  const time = lastSimTime.length >= 19 ? lastSimTime.slice(11, 19) : new Date().toLocaleTimeString('zh-CN', { hour12: false })
  const push = (content: string, level: Event['level'] = 'info') => events.push({ id: ++eventSeq, time, level, content })

  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const tasks: any[] = await request('/tasks/getNewTasksByCondition')
    const hasSnapshot = Object.keys(prevTaskStatus).length > 0
    for (const t of Array.isArray(tasks) ? tasks : []) {
      const prev = prevTaskStatus[t.task_name]
      if (prev === undefined) {
        if (hasSnapshot) push(`发现新任务 ${t.task_name}`)
      } else if (prev !== t.status) {
        push(`任务 ${t.task_name} 状态变更：${prev} → ${t.status}`, t.status === '正在执行' ? 'warning' : 'info')
      }
      prevTaskStatus[t.task_name] = t.status
    }
  } catch { /* 后端未就绪时静默 */ }

  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sats: any[] = await request('/satellites/getAllSatellites', { method: 'POST', body: { sate_name: '' } })
    for (const s of Array.isArray(sats) ? sats : []) {
      if (typeof s.battery === 'number' && s.battery < 20 && !lowBatteryWarned.has(s.name)) {
        lowBatteryWarned.add(s.name)
        push(`卫星 ${s.name} 电量过低（${s.battery}Wh），请注意`, 'alarm')
      }
    }
  } catch { /* 静默 */ }

  try {
    const j = await request('/getPlanningEvaluation')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const evaluation: any[] = j?.evaluation ?? []
    if (evaluation.length > 0) {
      const sat = Math.round((evaluation[evaluation.length - 1].task_satisfaction || 0) * 100)
      if (lastSatisfaction !== null && lastSatisfaction !== sat) push(`任务规划完成，满足率 ${sat}%`)
      lastSatisfaction = sat
    }
  } catch { /* 静默 */ }

  return events
}

/** GET /getCzml —— 真实 CZML 轨道数据数组（当前 3D 场景自算轨道，此接口备用） */
export async function getCzml() {
  try {
    return await request('/getCzml')
  } catch (e) {
    console.warn('[api] getCzml 失败:', e)
    return []
  }
}

// ==================== 卫星管理 ====================

/** GET /satellites/getSatelliteByName/{name} */
export async function getSatelliteByName(name: string): Promise<Satellite | undefined> {
  try {
    const d = await request(`/satellites/getSatelliteByName/${encodeURIComponent(name)}`)
    return d && d.id !== undefined ? mapSatDetail(d) : undefined
  } catch (e) {
    console.warn('[api] getSatelliteByName 失败:', e)
    return undefined
  }
}

/** GET /satellites/getSatelliteById/{id} */
export async function getSatelliteById(id: number): Promise<Satellite | undefined> {
  try {
    const d = await request(`/satellites/getSatelliteById/${id}`)
    return d && d.id !== undefined ? mapSatDetail(d) : undefined
  } catch (e) {
    console.warn('[api] getSatelliteById 失败:', e)
    return undefined
  }
}

/** POST /satellites/setSatelliteProperty/{id} —— 页面字段 → 后端字段映射 */
export async function setSatelliteProperty(id: number, props: Partial<Satellite>) {
  const body: Record<string, unknown> = {}
  if (props.storage !== undefined) body.storage = props.storage
  if (props.battery !== undefined) body.battery = props.battery
  if (props.downlinkRate !== undefined) body.downlink_rate = props.downlinkRate
  if (props.power) {
    if (props.power.idle !== undefined) body.eclipse_powers = props.power.idle
    if (props.power.solar !== undefined) body.sunlight_powers = props.power.solar
    if (props.power.maneuver !== undefined) body.maneuver_powers = props.power.maneuver
    if (props.power.imaging !== undefined) body.imaging_powers = props.power.imaging
  }
  if (props.payload) {
    if (props.payload.rotateSpeed !== undefined) body.angle_velocity = props.payload.rotateSpeed
    if (props.payload.stableTime !== undefined) body.stable_time = props.payload.stableTime
    if (props.payload.maxRoll !== undefined) body.side_swing_angle_Max = props.payload.maxRoll
    if (props.payload.maxPitch !== undefined) body.pitch_angle_Max = props.payload.maxPitch
    if (props.payload.cloudThreshold !== undefined) body.cloud_threshold = props.payload.cloudThreshold
  }
  if (props.sensorType !== undefined) body.loadType = SENSOR_EN[props.sensorType] ?? props.sensorType
  if (props.resolution !== undefined) body.resolution = props.resolution
  return action(request(`/satellites/setSatelliteProperty/${id}`, { method: 'POST', body }))
}

/** POST /satellites/setSatelliteAvailable/{id} | setSatelliteUnavailable/{id} */
export async function setSatelliteAvailable(id: number, available: boolean) {
  return action(request(`/satellites/${available ? 'setSatelliteAvailable' : 'setSatelliteUnavailable'}/${id}`, { method: 'POST' }))
}

/** GET /satellites/exportSatelliteInfo/{id} | /satellites/exportAllSatelliteInfo —— 浏览器下载 xlsx */
export async function exportSatelliteInfo(id?: number) {
  try {
    if (id !== undefined) {
      return await downloadFile(`/satellites/exportSatelliteInfo/${id}`, { fallbackName: `satellite_${id}_info.xlsx` })
    }
    return await downloadFile('/satellites/exportAllSatelliteInfo', { fallbackName: 'all_satellites_info.xlsx' })
  } catch (e) {
    console.error('[api] exportSatelliteInfo 失败:', e)
    return { code: 400 }
  }
}

// ==================== 任务管理 ====================

/** POST /tasks/getNewTasks —— 全部未完成任务（page_size 拉满，分页由前端处理） */
export async function getNewTasks(): Promise<Task[]> {
  try {
    const j = await request('/tasks/getNewTasks', { method: 'POST', body: { page: 1, page_size: 1000 } })
    return (j?.data?.items ?? []).map(mapTask)
  } catch (e) {
    console.warn('[api] getNewTasks 失败:', e)
    return []
  }
}

/** POST /tasks/getOldTasks —— 已完成任务 */
export async function getOldTasks(): Promise<Task[]> {
  try {
    const j = await request('/tasks/getOldTasks', { method: 'POST', body: { page: 1, page_size: 1000 } })
    return (j?.data?.items ?? []).map(mapTask)
  } catch (e) {
    console.warn('[api] getOldTasks 失败:', e)
    return []
  }
}

/** 任务表单字段（与后端 generate_single_task / edit_task 入参对齐） */
export interface TaskFormPayload {
  id?: number
  name?: string
  type: string            // 点目标/区域目标/移动目标/周期观测 等
  priority: number
  emergency: boolean
  sensorType?: string     // 中文载荷类型，映射为 optical/SAR/infrared
  resolution?: number
  startTime?: string      // 'YYYY-MM-DD HH:mm:ss' 本地时间
  endTime?: string
  cycle?: string          // 周期（分）
  cloudThickness?: number
  cluster?: string
  appointTime?: string
  coordinates: string[]   // ['纬度,经度', ...]，区域目标可多个
}

/** POST /tasks/addSingleTask | /tasks/updateTask/{id} —— 新增/编辑任务（字段与后端入参格式一致） */
export async function saveTask(t: Partial<TaskFormPayload>) {
  if (!t || !t.type) return { code: 400, msg: '缺少任务类型' }
  const body: Record<string, unknown> = {
    type: t.type,
    priority: t.priority ?? 1,
    is_urgent: t.emergency ? '是' : '否',
    payload: t.sensorType ? SENSOR_EN[t.sensorType] ?? t.sensorType : '',
    resolution: t.resolution,
    timeRanges: [t.startTime && t.endTime ? `${t.startTime},${t.endTime}` : ''],
    cycle: t.cycle ?? '',
    cloud_thickness: t.cloudThickness ?? 0,
    cluster_name: t.cluster ?? '',
    appoint_time: t.appointTime ?? '',
    coordinates: t.coordinates ?? [],
  }
  if (t.id !== undefined) {
    if (t.name) body.task_name = t.name // 仅编辑时允许改名
    return action(request(`/tasks/updateTask/${t.id}`, { method: 'POST', body }))
  }
  return action(request('/tasks/addSingleTask', { method: 'POST', body }))
}

/** POST /tasks/startTask/{id} */
export async function startTask(id: number) {
  return action(request(`/tasks/startTask/${id}`, { method: 'POST' }))
}

/** POST /tasks/pauseTask/{id} */
export async function pauseTask(id: number) {
  return action(request(`/tasks/pauseTask/${id}`, { method: 'POST' }))
}

/** POST /tasks/manualEndTask/{id} */
export async function manualEndTask(id: number) {
  return action(request(`/tasks/manualEndTask/${id}`, { method: 'POST' }))
}

/** DELETE /tasks/deleteTask/{id} */
export async function deleteTask(id: number) {
  return action(request(`/tasks/deleteTask/${id}`, { method: 'DELETE' }))
}

/** GET /tasks/exportTask/{id}（新任务）或 /tasks/exportOldTask/{id}（旧任务）| /tasks/exportAllNewTasks —— 浏览器下载 xlsx */
export async function exportTask(id?: number) {
  try {
    if (id !== undefined) {
      // 接口无法区分新旧任务：先试新任务导出，404 时回退旧任务导出
      try {
        return await downloadFile(`/tasks/exportTask/${id}`, { fallbackName: `task_${id}.xlsx` })
      } catch {
        return await downloadFile(`/tasks/exportOldTask/${id}`, { fallbackName: `old_task_${id}.xlsx` })
      }
    }
    return await downloadFile('/tasks/exportAllNewTasks', { fallbackName: 'new_tasks.xlsx' })
  } catch (e) {
    console.error('[api] exportTask 失败:', e)
    return { code: 400 }
  }
}

/** POST /tasks/addTasks（批量导入，FormData 字段名 file） */
export async function addTasks(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return action(request('/tasks/addTasks', { method: 'POST', formData: fd }))
}

// ==================== 星簇管理 ====================

/** POST /clusters/getClustersByPage —— 星簇列表（per_page 拉满，前端分页） */
export async function getClustersByPage(): Promise<Cluster[]> {
  try {
    const j = await request('/clusters/getClustersByPage', { method: 'POST', body: { page: 1, per_page: 500 } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (j?.data?.items ?? []).map((c: any): Cluster => ({
      id: c.id,
      name: c.name,
      orbits: (c.orbit_ids ?? []).map((n: number) => `第${n}轨道`),
      satelliteCount: c.satellite_count ?? c.number ?? 0,
      satellites: c.satellite_names ?? [],
      payloadSpec: c.payload_resolution ?? '',
      available: Boolean(c.status),
    }))
  } catch (e) {
    console.warn('[api] getClustersByPage 失败:', e)
    return []
  }
}

/** GET /clusters/getAllClustersNames —— 返回星簇名数组 */
export async function getAllClustersNames(): Promise<string[]> {
  try {
    const j = await request('/clusters/getAllClustersNames')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const names = (Array.isArray(j) ? j : []).map((c: any) => c.name ?? String(c))
    // 数据库中存在同名星簇（历史遗留脏数据），去重避免渲染重复选项/告警
    return [...new Set(names)] as string[]
  } catch (e) {
    console.warn('[api] getAllClustersNames 失败:', e)
    return []
  }
}

/** GET /clusters/getOrbits —— 后端返回 [{"10": "第10轨道..."}]，取描述文本 */
export async function getOrbits(): Promise<string[]> {
  try {
    const j = await request('/clusters/getOrbits')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (j?.orbits ?? []).map((o: any) => String(Object.values(o)[0] ?? ''))
  } catch (e) {
    console.warn('[api] getOrbits 失败:', e)
    return []
  }
}

/** GET /clusters/getClusterDetailsByName/{name} + 列表数据合并（详情接口仅返回载荷配置） */
export async function getClusterDetailsByName(name: string) {
  try {
    const [list, detail] = await Promise.all([
      getClustersByPage(),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      request(`/clusters/getClusterDetailsByName/${encodeURIComponent(name)}`).catch(() => null as any),
    ])
    const base = list.find((c) => c.name === name)
    return {
      name,
      satellites: base?.satellites ?? [],
      orbits: base?.orbits ?? [],
      payloadSpec: base?.payloadSpec ?? '',
      sensorTypes: detail?.sensor_type ?? [],
      payloadResolution: detail?.payload_resolution ?? {},
    }
  } catch (e) {
    console.warn('[api] getClusterDetailsByName 失败:', e)
    return undefined
  }
}

/** POST /clusters/addCluster | /clusters/updateCluster/{id} */
export async function saveCluster(c: Partial<Cluster>) {
  // 轨道描述字符串（第10轨道…）提取轨道编号；载荷配置按 "payload:res1,res2|..." 尽力解析
  const orbits = (c.orbits ?? []).flatMap((o) => {
    const m = String(o).match(/第(\d+)轨道/)
    return m ? [parseInt(m[1], 10)] : []
  })
  const payloadResolution: Record<string, number[]> = {}
  for (const part of String(c.payloadSpec ?? '').split('|')) {
    const [k, v] = part.split(':')
    const key = SENSOR_EN[k] ?? k
    if (!key) continue
    payloadResolution[key] = v ? v.split(',').map(Number).filter((n) => !isNaN(n)) : []
  }
  const body = { cluster_name: c.name, orbits, payload_resolution: payloadResolution }
  if (c.id !== undefined) {
    return action(request(`/clusters/updateCluster/${c.id}`, { method: 'POST', body }))
  }
  return action(request('/clusters/addCluster', { method: 'POST', body }))
}

/** DELETE /clusters/deleteClusterById/{id} */
export async function deleteClusterById(id: number) {
  return action(request(`/clusters/deleteClusterById/${id}`, { method: 'DELETE' }))
}

/** POST /clusters/setAvailableCluster/{id} | setUnavailableCluster/{id} */
export async function setAvailableCluster(id: number, available: boolean) {
  return action(request(`/clusters/${available ? 'setAvailableCluster' : 'setUnavailableCluster'}/${id}`, { method: 'POST' }))
}

/** POST /clusters/replan —— 跨簇重规划 */
export async function replanCluster(from: string, to: string) {
  return action(request('/clusters/replan', { method: 'POST', body: { oldCluster: from, newCluster: to } }))
}

/** POST /clusters/submitClusterFile（FormData 字段名 file，重建全部星簇） */
export async function submitClusterFile(f: File) {
  const fd = new FormData()
  fd.append('file', f)
  return action(request('/clusters/submitClusterFile', { method: 'POST', formData: fd }))
}

// ==================== 地面站 ====================

/** GET /satellites/groundStationInfo —— 响应结构与页面一致，直接透传 */
export async function getGroundStationInfo(): Promise<GroundStation[]> {
  try {
    const j = await request('/satellites/groundStationInfo')
    return Array.isArray(j) ? j : []
  } catch (e) {
    console.warn('[api] getGroundStationInfo 失败:', e)
    return []
  }
}

// ==================== 示范用例 ====================

type CaseType = 'point' | 'area' | 'ocean' | 'comprehensive'

export interface CaseInfo {
  type: CaseType
  name: string
  desc: string
  tags: string[]
  params: { label: string; value: string }[]
  region: { points: [number, number][]; polygon: [number, number][]; trajectory: [number, number][] }
  features: string[]
  steps: string[]
}

const CASE_URL: Record<CaseType, string> = {
  point: '/tasks/pointTargetCase',
  area: '/tasks/areaTargetCase',
  ocean: '/tasks/oceanTargetCase',
  comprehensive: '/tasks/comprehensiveCase',
}
const CASE_NAME: Record<CaseType, string> = { point: '点目标案例', area: '区域目标案例', ocean: '海洋搜救案例', comprehensive: '综合验证案例' }

// 用例展示文案（后端仅提供任务参数，描述/要点/流程为静态展示内容，与旧前端 Yongli.vue 一致）
const CASE_META: Record<CaseType, { desc: string; tags: string[]; features: string[]; steps: string[]; target: string }> = {
  point: {
    desc: '生成一批点目标观测任务，测试单点观测能力',
    tags: ['单点观测', '高分辨率', '快速响应'],
    features: ['目标为离散点，任务间相互独立', '考验单星快速侧摆指向能力', '验证高分辨率成像链路'],
    steps: ['生成任务', '任务规划', '卫星执行', '结果反馈'],
    target: '多重点目标',
  },
  area: {
    desc: '生成区域目标观测任务，测试大范围覆盖能力',
    tags: ['区域覆盖', '条带拼接', '协同观测'],
    features: ['区域需拆分为多条带协同覆盖', '考验星簇内多星任务分配均衡性', '验证条带拼接完整性评估'],
    steps: ['生成任务', '区域拆分', '多星协同', '拼接评估'],
    target: '陆地区域',
  },
  ocean: {
    desc: '生成海洋移动目标搜救任务，测试动态跟踪能力',
    tags: ['移动目标', '动态跟踪', '紧急响应'],
    features: ['目标位置随时间漂移，需要滚动重规划', '紧急任务抢占常规任务资源', '验证动态跟踪与告警链路'],
    steps: ['生成任务', '紧急规划', '接力跟踪', '告警反馈'],
    target: '海洋移动目标',
  },
  comprehensive: {
    desc: '技术指标验证场景：一批生成 21 个点目标、2 个区域目标、8 个移动目标，验证星簇级大规模协同规划能力',
    tags: ['大规模协同', '混合目标', '指标验证'],
    features: ['点/区域/移动三类目标混合入队', '考验单批次 30+ 目标的规划耗时', '验证星簇协同任务分配与资源约束'],
    steps: ['生成任务', '批量规划', '协同执行', '指标评估'],
    target: '混合目标群',
  },
}

/** GET /tasks/pointTargetCase | areaTargetCase | oceanTargetCase —— 执行用例并写入后端历史 */
export async function runCase(type: CaseType) {
  try {
    const j = await request(CASE_URL[type])
    const count = typeof j?.count === 'number' ? j.count : '若干'
    const message = j?.message ?? `${CASE_NAME[type]}执行成功，任务已生成并加入调度队列`
    // 持久化执行历史（同旧前端 addToHistory）
    await request('/tasks/caseHistory', {
      method: 'POST',
      body: { caseType: type, caseName: CASE_NAME[type], success: true, taskCount: typeof count === 'number' ? count : null, message },
    }).catch((e) => console.warn('[api] 写入用例历史失败:', e))
    const preset = await getPresetCaseInfo(type).catch(() => null)
    return {
      code: 200,
      caseType: CASE_NAME[type],
      // 后端不返回批次号，不编造，页面显示「—」
      taskId: '—',
      taskCount: count,
      genTime: fmtTime(new Date()),
      status: '已下发规划',
      sensorType: preset?.params.find((p) => p.label === '载荷类型')?.value ?? '—',
      satellites: preset?.params.find((p) => p.label === '所属星簇')?.value ?? '—',
      target: CASE_META[type].target,
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : '执行失败'
    await request('/tasks/caseHistory', {
      method: 'POST',
      body: { caseType: type, caseName: CASE_NAME[type], success: false, taskCount: null, message: msg },
    }).catch(() => undefined)
    return { code: 400, msg, caseType: CASE_NAME[type], taskId: '—', taskCount: 0, genTime: fmtTime(new Date()), status: '生成失败', sensorType: '—', satellites: '—', target: CASE_META[type].target }
  }
}

/** GET /tasks/presetCaseInfo/{type} —— 预置案例真实参数 + 静态展示文案 */
export async function getPresetCaseInfo(type: CaseType): Promise<CaseInfo> {
  const meta = CASE_META[type]
  try {
    const j = await request(`/tasks/presetCaseInfo/${type}`)
    const d = j?.data ?? {}
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const points: [number, number][] = (d.points ?? []).filter((p: any) => Array.isArray(p) && p.length >= 2)
    return {
      type,
      name: d.caseName ?? CASE_NAME[type],
      desc: meta.desc,
      tags: meta.tags,
      params: [
        { label: '优先级', value: String(d.priority ?? '—') },
        { label: '是否紧急', value: String(d.isEmergency ?? '—') },
        { label: '载荷类型', value: d.sensorType ? toSensor(d.sensorType) : '—' },
        { label: '分辨率', value: d.resolution != null ? `${d.resolution} m` : '—' },
        { label: '所属星簇', value: d.clusterName ?? '—' },
        { label: '云层厚度', value: d.cloudThickness != null ? `${d.cloudThickness} m` : '不限' },
        { label: '时间范围', value: String(d.timeRange ?? '—') },
      ],
      // 点目标：离散点；区域目标：多点构成边界多边形；海洋：目标点连成示意轨迹（同旧前端地图逻辑）
      region: {
        points: type === 'point' ? points : type === 'ocean' ? points : [],
        polygon: type === 'area' && points.length > 2 ? points : [],
        trajectory: type === 'ocean' && points.length > 1 ? points : [],
      },
      features: meta.features,
      steps: meta.steps,
    }
  } catch (e) {
    console.warn('[api] getPresetCaseInfo 失败:', e)
    return {
      type, name: CASE_NAME[type], desc: meta.desc, tags: meta.tags, params: [],
      region: { points: [], polygon: [], trajectory: [] }, features: meta.features, steps: meta.steps,
    }
  }
}

/** GET /tasks/caseResult/{type} —— 最近一次归档执行结果（404 表示暂无归档） */
export async function getCaseResult(type: CaseType) {
  try {
    const j = await request(`/tasks/caseResult/${type}`)
    const d = j?.data
    if (!d) return { type, lastRun: undefined }
    return {
      type,
      lastRun: { name: d.taskName ?? CASE_NAME[type], success: d.status === 'Success', count: 1, time: String(d.endTime ?? '') },
    }
  } catch {
    return { type, lastRun: undefined }
  }
}

/** GET /tasks/caseHistory —— 执行历史（最近 20 条） */
export async function getCaseHistory() {
  try {
    const j = await request('/tasks/caseHistory')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (Array.isArray(j) ? j : []).map((h: any) => ({
      name: h.caseName ?? '',
      success: Boolean(h.success),
      count: h.taskCount ?? '若干',
      time: h.time ?? '',
    }))
  } catch (e) {
    console.warn('[api] getCaseHistory 失败:', e)
    return []
  }
}

/** DELETE /tasks/caseHistory —— 清空执行历史 */
export async function clearCaseHistory() {
  return action(request('/tasks/caseHistory', { method: 'DELETE' }))
}

// ==================== 性能分析 ====================

/** GET /getModel —— 当前规划模式（0 最优方案 / 1 满足率 / 2 资源利用率 / 3 成像质量） */
export async function getModel() {
  try {
    const j = await request('/getModel')
    return { mode: j?.mode ?? 0, auto: true }
  } catch (e) {
    console.warn('[api] getModel 失败:', e)
    return { mode: 0, auto: true }
  }
}

/** GET /getClusterData/{clusterName}（Tab1 算法性能）——status 可能为 null */
export async function getClusterData(cluster: string) {
  const empty = { time: [] as string[], taskCount: [] as number[], power: [] as number[], storage: [] as number[], storageRate: [] as number[] }
  try {
    const j = await request(`/getClusterData/${encodeURIComponent(cluster)}`)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data: any[] = j?.data ?? []
    if (!Array.isArray(data) || data.length === 0) return empty
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const getVal = (item: any, key: string) => {
      const s = item.status && typeof item.status === 'object' ? item.status : item
      return Number(s?.[key] || 0)
    }
    return {
      time: data.map((i) => String(i.time ?? '').slice(5, 16)),
      taskCount: data.map((i) => getVal(i, 'cluster_tasks_count')),
      power: data.map((i) => Math.round(getVal(i, 'cluster_battery_cost') * 100) / 100),
      storage: data.map((i) => Math.round(getVal(i, 'cluster_storage_cost') * 100) / 100),
      storageRate: data.map((i) => Math.round(getVal(i, 'cluster_storage_utilization') * 10000) / 100),
    }
  } catch (e) {
    console.warn('[api] getClusterData 失败:', e)
    return empty
  }
}

/** GET /exportScheduleStatus + /getPlanningEvaluation + /tasks/getOldTasksByCondition（Tab2 系统性能聚合） */
export async function getScheduleStatus() {
  const round2 = (v: number) => Math.round((v || 0) * 100) / 100
  const empty = {
    time: [] as string[],
    stats: { completeRate: 0, resourceRate: 0, avgPlanTime: 0, planCount: 0 },
    compare: {
      completeRate: {} as Record<string, number[]>, power: {} as Record<string, number[]>,
      storage: {} as Record<string, number[]>, planTime: {} as Record<string, number[]>,
    },
    radar: { indicators: ['完成率', '资源利用率', '成像质量', '响应速度'], 贪心: [] as number[], 蚁群: [] as number[], 遗传: [] as number[] },
    execution: { labels: [] as string[], success: [] as number[], fail: [] as number[] },
    table: [] as { algo: string; complete: number; resource: number; quality: number; power: number; storage: number; planTime: number; time: string }[],
  }
  try {
    const [evRes, oldTasks] = await Promise.all([
      request('/getPlanningEvaluation'),
      request('/tasks/getOldTasksByCondition').catch(() => []),
    ])
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const evals: any[] = evRes?.evaluation ?? []
    if (evals.length === 0) return empty
    const latest = evals[evals.length - 1]
    const duration = Number(latest.duration || 0)
    // 响应速度得分：规划耗时 0~60s 线性映射 100~0（同旧前端雷达图）
    const responseScore = Math.max(0, Math.min(100, Math.round(100 - (duration / 60) * 100)))
    const ALGOS = [
      { key: 'greedy', name: '贪心', fullName: '贪心算法' },
      { key: 'ant_colony', name: '蚁群', fullName: '蚁群算法' },
      { key: 'genetic', name: '遗传', fullName: '遗传算法' },
    ] as const
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const metric = (e: any, key: string) => e?.[key] ?? {}
    const series = (field: string, scale = 1) => ({
      蚁群: evals.map((e) => round2((metric(e, 'ant_colony')[field] || 0) * scale)),
      遗传: evals.map((e) => round2((metric(e, 'genetic')[field] || 0) * scale)),
      贪心: evals.map((e) => round2((metric(e, 'greedy')[field] || 0) * scale)),
      当前方案: evals.map((e) => round2((e[field] || 0) * scale)),
    })
    const algosLatest = ALGOS.map((a) => metric(latest, a.key)).filter((m) => m && Object.keys(m).length > 0)
    const avgUtil = algosLatest.length > 0
      ? algosLatest.reduce((sum, m) => sum + (m.resource_utilization || 0), 0) / algosLatest.length
      : 0
    const avgDuration = evals.reduce((sum, e) => sum + (e.duration || 0), 0) / evals.length
    // 各类型任务执行情况（来自已完成任务归档）
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const oldList: any[] = Array.isArray(oldTasks) ? oldTasks : []
    const execTypes = [...new Set(oldList.map((t) => String(t.type ?? '')))].filter(Boolean)
    return {
      time: evals.map((_, i) => `第${i + 1}轮`),
      stats: {
        completeRate: Math.round((latest.task_satisfaction || 0) * 100),
        resourceRate: Math.round(avgUtil * 100),
        avgPlanTime: round2(avgDuration),
        planCount: evals.length,
      },
      compare: {
        completeRate: series('task_satisfaction', 100),
        power: series('overall_battery_cost'),
        storage: series('overall_storage_cost'),
        // 规划耗时后端仅记录当前方案
        planTime: { 当前方案: evals.map((e) => round2(e.duration)) },
      },
      radar: {
        indicators: ['完成率', '资源利用率', '成像质量', '响应速度'],
        贪心: [Math.round((metric(latest, 'greedy').task_satisfaction || 0) * 100), Math.round((metric(latest, 'greedy').resource_utilization || 0) * 100), Math.round((metric(latest, 'greedy').imaging_quality || 0) * 100), responseScore],
        蚁群: [Math.round((metric(latest, 'ant_colony').task_satisfaction || 0) * 100), Math.round((metric(latest, 'ant_colony').resource_utilization || 0) * 100), Math.round((metric(latest, 'ant_colony').imaging_quality || 0) * 100), responseScore],
        遗传: [Math.round((metric(latest, 'genetic').task_satisfaction || 0) * 100), Math.round((metric(latest, 'genetic').resource_utilization || 0) * 100), Math.round((metric(latest, 'genetic').imaging_quality || 0) * 100), responseScore],
      },
      execution: {
        labels: execTypes,
        success: execTypes.map((tp) => oldList.filter((t) => t.type === tp && t.status === 'Success').length),
        fail: execTypes.map((tp) => oldList.filter((t) => t.type === tp && t.status === 'Failed').length),
      },
      table: [
        ...ALGOS.map((a) => ({
          algo: a.fullName,
          complete: Math.round((metric(latest, a.key).task_satisfaction || 0) * 100),
          resource: Math.round((metric(latest, a.key).resource_utilization || 0) * 100),
          quality: Math.round((metric(latest, a.key).imaging_quality || 0) * 100),
          power: round2(metric(latest, a.key).overall_battery_cost || 0),
          storage: round2(metric(latest, a.key).overall_storage_cost || 0),
          planTime: round2(duration),
          time: String(latest.time ?? '-'),
        })),
        {
          algo: '当前方案',
          complete: Math.round((latest.task_satisfaction || 0) * 100),
          resource: Math.round(avgUtil * 100),
          quality: Math.round((latest.imaging_quality || 0) * 100),
          power: round2(latest.overall_battery_cost || 0),
          storage: round2(latest.overall_storage_cost || 0),
          planTime: round2(duration),
          time: String(latest.time ?? '-'),
        },
      ],
    }
  } catch (e) {
    console.warn('[api] getScheduleStatus 失败:', e)
    return empty
  }
}

/** POST /exportSchedule/{greedy|ant|genetic|schedule} —— 浏览器下载方案 txt */
export async function exportSchedule(type: string) {
  const names: Record<string, string> = { greedy: '贪心算法方案.txt', ant: '蚁群算法方案.txt', genetic: '遗传算法方案.txt', schedule: '所选方案.txt' }
  try {
    // 后端要求 JSON 请求体（可带 number 批次号，缺省取最新批次）
    return await downloadFile(`/exportSchedule/${type}`, { method: 'POST', body: {}, fallbackName: names[type] ?? `${type}.txt` })
  } catch (e) {
    console.error('[api] exportSchedule 失败:', e)
    return { code: 400 }
  }
}

// ==================== 系统设置 ====================

/** GET /isSubmitTle | /isSubmitSat | /isSubmitSys —— 数据提交状态 */
export async function getSubmitStatus() {
  try {
    const [tle, sat, sys] = await Promise.all([
      request('/isSubmitTle'),
      request('/isSubmitSat'),
      request('/isSubmitSys'),
    ])
    return {
      tle: Boolean(tle?.is_submit_tle),
      sat: Boolean(sat?.is_submit_sat),
      sys: Boolean(sys?.is_submit_sys),
    }
  } catch (e) {
    console.warn('[api] getSubmitStatus 失败:', e)
    return { tle: false, sat: false, sys: false }
  }
}

/** 仿真参数保存：页面仅提供时间倍率，映射为 POST /changeTimeMultiple（form 字段 time_multiple） */
export async function saveSimParameters(p: unknown) {
  const speed = Number((p as { speed?: number })?.speed) || 0
  if (speed >= 1) {
    const fd = new FormData()
    fd.append('time_multiple', String(Math.round(speed)))
    return action(request('/changeTimeMultiple', { method: 'POST', formData: fd }))
  }
  return { code: 200 }
}

/** POST /initTLE（FormData 字段名 file） */
export async function initTLE(f: File) {
  const fd = new FormData()
  fd.append('file', f)
  return action(request('/initTLE', { method: 'POST', formData: fd }))
}

/** POST /initFiles（批量导入卫星参数，FormData 字段名 file） */
export async function initFiles(f: File) {
  const fd = new FormData()
  fd.append('file', f)
  return action(request('/initFiles', { method: 'POST', formData: fd }))
}

/** GET /exportTleFile —— 浏览器下载 TLE.txt */
export async function exportTleFile() {
  try {
    return await downloadFile('/exportTleFile', { fallbackName: 'TLE.txt' })
  } catch (e) {
    console.error('[api] exportTleFile 失败:', e)
    return { code: 400 }
  }
}

/** POST /networkParametersList —— 卫星参数列表批量提交（后端要求每项含 name 字段） */
export async function submitNetworkParametersList(list: unknown[]) {
  const mapped = (list as Record<string, unknown>[]).map((i) => {
    const loadType = SENSOR_EN[String(i.sensorType ?? '')] ?? String(i.sensorType ?? 'optical')
    return {
      ...i,
      name: String(i.name ?? loadType),
      loadType,
      imaging_powers: i.imagingPower ?? i.imaging_powers,
    }
  })
  return action(request('/networkParametersList', { method: 'POST', body: { list: mapped } }))
}

/** POST /networkParameters —— 按载荷批量设置（后端键为 optical/SAR/infrared，九项载荷参数全量提交） */
export async function saveNetworkParameters(p: unknown) {
  const src = p as Record<string, Partial<PayloadParams>>
  const body: Record<string, Record<string, unknown>> = {}
  for (const [zh, en] of Object.entries(SENSOR_EN)) {
    const v = src?.[zh]
    if (!v) continue
    body[en] = {
      storage: v.storage, battery: v.battery, resolution: v.resolution,
      pitchAngle: v.pitchAngle, sideAngle: v.sideAngle, settlingTime: v.settlingTime,
      angularVelocity: v.angularVelocity, width: v.width, threshold: v.threshold,
      downlink_rate: v.downlink_rate, sunlight_powers: v.sunlight_powers,
      maneuver_powers: v.maneuver_powers, imaging_powers: v.imaging_powers,
      eclipse_powers: v.eclipse_powers,
    }
  }
  // 三类载荷必须齐全，缺省的用空对象（后端填默认值）
  for (const en of ['optical', 'SAR', 'infrared']) {
    if (!body[en]) body[en] = {}
  }
  return action(request('/networkParameters', { method: 'POST', body }))
}

/** 载荷参数（与后端 network_config 前端字段名一致） */
export interface PayloadParams {
  storage: number        // 存储容量 GB
  battery: number        // 电池容量 Wh
  resolution: number     // 分辨率 m
  width: number          // 幅宽最大值 km
  sideAngle: number      // 最大侧摆角 °
  pitchAngle: number     // 最大俯仰角 °
  angularVelocity: number // 载荷转动角速度 rad/s
  settlingTime: number   // 稳定时间 s
  threshold: number      // 云层遮挡厚度阈值 m
  downlink_rate?: number
  sunlight_powers?: number
  maneuver_powers?: number
  imaging_powers?: number
  eclipse_powers?: number
}

/** GET /networkParameters —— 查询当前三类载荷配置（optical/SAR/infrared → 中文键返回） */
export async function getNetworkParameters(): Promise<Record<string, PayloadParams> | null> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const j: any = await request('/networkParameters')
    if (!j || typeof j !== 'object') return null
    const result: Record<string, PayloadParams> = {}
    for (const [zh, en] of Object.entries(SENSOR_EN)) {
      if (j[en]) result[zh] = j[en] as PayloadParams
    }
    return Object.keys(result).length ? result : null
  } catch (e) {
    console.warn('[api] getNetworkParameters 失败:', e)
    return null
  }
}

/** GET /getAutoRun —— 查询运行模式（true=自主运行，false=程序控制） */
export async function getAutoRun(): Promise<boolean> {
  try {
    const j = await request('/getAutoRun')
    return Boolean(j?.auto ?? true)
  } catch (e) {
    console.warn('[api] getAutoRun 失败:', e)
    return true
  }
}

/** POST /changeAutoRun —— 切换运行模式 */
export async function changeAutoRun(auto: boolean) {
  return action(request('/changeAutoRun', { method: 'POST', body: { auto } }))
}

/** POST /changeModel —— 设置规划方案（0综合最优/1任务满足率/2资源利用率/3成像质量）；后端要求 body 为裸整数 */
export async function setModel(mode: number) {
  return action(request('/changeModel', { method: 'POST', body: mode }))
}

export interface ConstraintItem {
  key: 'time' | 'energy' | 'storage'
  name: string
  enabled: boolean
  threshold: number
  unit: string
  desc: string
}

/** GET /constraintConfig —— 查询星簇级约束项配置 */
export async function getConstraintConfig(): Promise<ConstraintItem[]> {
  try {
    const j = await request('/constraintConfig')
    return Array.isArray(j?.constraints) ? j.constraints : []
  } catch (e) {
    console.warn('[api] getConstraintConfig 失败:', e)
    return []
  }
}

/** POST /constraintConfig —— 更新星簇级约束项（启用状态/阈值） */
export async function saveConstraintConfig(constraints: Partial<ConstraintItem>[]) {
  return action(request('/constraintConfig', { method: 'POST', body: { constraints } }))
}

/** POST /simulateParameters —— 提交仿真起止时间与三权重（本地时间字符串，后端统一转 UTC） */
export async function saveSimConfig(p: { startTime: string; endTime: string; completed: number; balance: number; priority: number }) {
  return action(request('/simulateParameters', {
    method: 'POST',
    body: {
      date1: p.startTime,
      date2: p.endTime,
      completed_gravity: p.completed,
      balance_gravity: p.balance,
      priority_gravity: p.priority,
    },
  }))
}

/** GET /clusters/exportAllClusters —— 导出全部星簇 xlsx */
export async function exportAllClusters() {
  try {
    return await downloadFile('/clusters/exportAllClusters', { fallbackName: '星簇信息.xlsx' })
  } catch (e) {
    console.error('[api] exportAllClusters 失败:', e)
    return { code: 400 }
  }
}

/** POST /clusters/getInfoByOrbits —— 查询选定轨道（轨道编号数组，如 [10]）的载荷-分辨率选项 */
export async function getOrbitPayloadInfo(orbits: number[]): Promise<Record<string, number[]>> {
  try {
    const j = await request('/clusters/getInfoByOrbits', { method: 'POST', body: { orbits } })
    return j?.resolution_map ?? {}
  } catch (e) {
    console.warn('[api] getOrbitPayloadInfo 失败:', e)
    return {}
  }
}
