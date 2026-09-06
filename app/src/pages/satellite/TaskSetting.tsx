import { useEffect, useState } from 'react'
import { Upload } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { PageHeader, FormRow, Switch } from '@/components/ui/widgets'
import Chart, { AXIS_STYLE, TOOLTIP_STYLE } from '@/components/Chart'
import { getPlanningEvaluation, saveTask, addTasks, getAllClustersNames, getClusterDetailsByName } from '@/api'

const TASK_TYPES = ['点目标', '区域目标', '广域目标', '移动目标', '静态观测', '周期观测']
/** 区域/广域目标允许多个坐标点，其余类型只保留 1 个 */
const MULTI_COORD_TYPES = ['区域目标', '广域目标']
const SENSOR_FROM_KEY: Record<string, string> = { optical: '光学', SAR: 'SAR', infrared: '红外' }
const ALL_SENSORS = Object.values(SENSOR_FROM_KEY)

interface CoordPoint { lat: string; lon: string }

interface NewTaskForm {
  type: string
  cluster: string
  priority: number
  emergency: boolean
  sensorType: string
  resolution: string
  startTime: string
  endTime: string
  cycle: string
  cloudThickness: string
  appointTime: string
  coords: CoordPoint[]
}

const EMPTY_FORM: NewTaskForm = {
  type: '', cluster: '', priority: 1, emergency: false, sensorType: '', resolution: '',
  startTime: '', endTime: '', cycle: '', cloudThickness: '', appointTime: '', coords: [{ lat: '', lon: '' }],
}

/** datetime-local 值 → 后端 'YYYY-MM-DD HH:mm:ss' */
const toBackendTime = (s: string) => (s ? `${s.replace('T', ' ')}${s.length === 16 ? ':00' : ''}` : '')

// 后端无规划参数下发/查询接口：配置持久化在 localStorage，页面如实提示
const LS_KEY = 'task_planning_params'
const DEFAULTS = { algo: '蚁群算法', period: '300', window: '10', maxTime: '60', mergeThreshold: '0.85', preempt: '开启' }

function loadParams() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch { /* 忽略损坏的本地缓存 */ }
  return { ...DEFAULTS }
}

export default function TaskSetting() {
  const [params, setParams] = useState(loadParams)
  const [evalData, setEvalData] = useState<any>(null)
  const [saved, setSaved] = useState(false)

  // 新增任务表单
  const [form, setForm] = useState<NewTaskForm>({ ...EMPTY_FORM, coords: [{ lat: '', lon: '' }] })
  const [clusters, setClusters] = useState<string[]>([])
  const [sensors, setSensors] = useState<string[]>(ALL_SENSORS)
  const [submitMsg, setSubmitMsg] = useState('')
  const [importMsg, setImportMsg] = useState('')

  useEffect(() => { getAllClustersNames().then(setClusters) }, [])

  // 星簇 → 载荷类型联动：解析星簇载荷配置，只保留支持的载荷；未选/解析失败显示全部
  useEffect(() => {
    if (!form.cluster) { setSensors(ALL_SENSORS); return }
    getClusterDetailsByName(form.cluster).then((d) => {
      const keys = new Set<string>()
      if (d?.payloadResolution && typeof d.payloadResolution === 'object') {
        Object.keys(d.payloadResolution).forEach((k) => keys.add(k))
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const spec = (d as any)?.payload ?? d?.payloadSpec // 'optical:0.5,1|SAR:2' 形式
      if (typeof spec === 'string') {
        spec.split('|').forEach((seg) => { const k = seg.split(':')[0]?.trim(); if (k) keys.add(k) })
      }
      const list = Object.entries(SENSOR_FROM_KEY).filter(([k]) => keys.has(k)).map(([, v]) => v)
      setSensors(list.length ? list : ALL_SENSORS)
    }).catch(() => setSensors(ALL_SENSORS))
  }, [form.cluster])

  // 载荷列表收缩时清掉不再受支持的选中项
  useEffect(() => {
    if (form.sensorType && !sensors.includes(form.sensorType)) setForm((f) => ({ ...f, sensorType: '' }))
  }, [sensors]) // eslint-disable-line react-hooks/exhaustive-deps

  const isMultiCoord = MULTI_COORD_TYPES.includes(form.type)
  const coords = isMultiCoord ? form.coords : form.coords.slice(0, 1)

  const setCoord = (i: number, k: keyof CoordPoint, v: string) =>
    setForm({ ...form, coords: form.coords.map((c, j) => (j === i ? { ...c, [k]: v } : c)) })

  const importFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) addTasks(f).then((r) => setImportMsg(r?.code === 200 ? '✓ 批量导入成功' : `导入失败：${r?.msg ?? '未知错误'}`)) // POST /tasks/addTasks
    e.target.value = ''
  }

  const submitTask = async () => {
    if (!form.type) return setSubmitMsg('请选择任务类型')
    const pts = form.coords.filter((c) => c.lat !== '' || c.lon !== '')
    if (!pts.length) return setSubmitMsg('请至少填写 1 个目标坐标点')
    for (const c of pts) {
      const lat = Number(c.lat)
      const lon = Number(c.lon)
      if (c.lat === '' || c.lon === '' || isNaN(lat) || isNaN(lon)) return setSubmitMsg('坐标点纬度/经度需填写完整')
      if (lat < -90 || lat > 90) return setSubmitMsg('纬度需在 -90 ~ 90 之间')
      if (lon < -180 || lon > 180) return setSubmitMsg('经度需在 -180 ~ 180 之间')
    }
    if (isMultiCoord && pts.length < 3) return setSubmitMsg('区域/广域目标至少需要 3 个坐标点')
    if (form.startTime && form.endTime && form.startTime > form.endTime) return setSubmitMsg('开始时间不能晚于结束时间')
    const r = await saveTask({
      type: form.type,
      priority: form.priority,
      emergency: form.emergency,
      sensorType: form.sensorType || undefined,
      resolution: form.resolution ? Number(form.resolution) : undefined,
      startTime: toBackendTime(form.startTime) || undefined,
      endTime: toBackendTime(form.endTime) || undefined,
      cycle: form.cycle || undefined,
      cloudThickness: form.cloudThickness ? Number(form.cloudThickness) : undefined,
      cluster: form.cluster || undefined,
      appointTime: toBackendTime(form.appointTime) || undefined,
      coordinates: pts.map((c) => `${c.lat},${c.lon}`),
    })
    if (r?.code === 200) {
      setSubmitMsg('✓ 任务已创建并加入调度队列')
      setForm({ ...EMPTY_FORM, coords: [{ lat: '', lon: '' }] })
    } else {
      setSubmitMsg(`创建失败：${r?.msg ?? '未知错误'}`)
    }
  }

  useEffect(() => {
    getPlanningEvaluation().then(setEvalData) // POST /tasks/getPlanningEvaluation
  }, [])

  const trend: { round: number; rate: number }[] = evalData?.trend ?? []
  const taskStats = evalData?.taskStats ?? { waiting: 0, running: 0, done: 0 }

  const trendOption = {
    grid: { left: 44, right: 16, top: 24, bottom: 26 },
    tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
    xAxis: { type: 'category', data: trend.map((p) => `T${p.round}`), ...AXIS_STYLE },
    yAxis: { type: 'value', max: 100, name: '%', ...AXIS_STYLE },
    series: [{
      name: '任务满足率', type: 'line', data: trend.map((p) => p.rate), smooth: true, symbol: 'circle', symbolSize: 5,
      lineStyle: { color: '#00dcff', width: 2 },
      itemStyle: { color: '#00dcff' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,220,255,0.25)' }, { offset: 1, color: 'rgba(0,0,0,0)' }] } },
    }],
  }

  const statsOption = {
    grid: { left: 44, right: 16, top: 24, bottom: 26 },
    tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
    xAxis: { type: 'category', data: ['等待执行', '执行中', '已完成'], ...AXIS_STYLE },
    yAxis: { type: 'value', ...AXIS_STYLE },
    series: [{
      type: 'bar', data: [taskStats.waiting, taskStats.running, taskStats.done], barWidth: 18,
      itemStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#00dcff' }, { offset: 1, color: 'rgba(0,220,255,0.15)' }] },
        borderRadius: [3, 3, 0, 0],
      },
    }],
  }

  const handleSave = () => {
    localStorage.setItem(LS_KEY, JSON.stringify(params))
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handleReset = () => {
    localStorage.removeItem(LS_KEY)
    setParams({ ...DEFAULTS })
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader title="任务设置" sub="TASK SETTING" />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        {/* 新增任务 */}
        <Panel
          title="新增任务"
          sub="NEW TASK"
          className="xl:col-span-3"
          right={
            <label className="tech-btn flex cursor-pointer items-center gap-1">
              <Upload size={12} />批量导入<input type="file" accept=".txt,.csv,.json,.xlsx" className="hidden" onChange={importFile} />
            </label>
          }
        >
          {importMsg && <div className={`mb-2 text-xs ${importMsg.startsWith('✓') ? 'text-[#4fe3a5]' : 'text-[#ff8d8d]'}`}>{importMsg}</div>}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <FormRow label="任务类型" required>
              <select
                className="tech-input"
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value, coords: MULTI_COORD_TYPES.includes(e.target.value) ? form.coords : form.coords.slice(0, 1) })}
              >
                <option value="">请选择</option>
                {TASK_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </FormRow>
            <FormRow label="所属星簇">
              <select className="tech-input" value={form.cluster} onChange={(e) => setForm({ ...form, cluster: e.target.value })}>
                <option value="">不指定</option>
                {clusters.map((c) => <option key={c}>{c}</option>)}
              </select>
            </FormRow>
            <FormRow label="优先级（1-5）">
              <input className="tech-input" type="number" min={1} max={5} value={form.priority} onChange={(e) => setForm({ ...form, priority: Math.min(5, Math.max(1, Number(e.target.value) || 1)) })} />
            </FormRow>
            <FormRow label="是否紧急">
              <div className="flex h-8 items-center"><Switch checked={form.emergency} onChange={(v) => setForm({ ...form, emergency: v })} /></div>
            </FormRow>
            <FormRow label="载荷类型">
              <select className="tech-input" value={form.sensorType} onChange={(e) => setForm({ ...form, sensorType: e.target.value })}>
                <option value="">请选择</option>
                {sensors.map((s) => <option key={s}>{s}</option>)}
              </select>
            </FormRow>
            <FormRow label="分辨率 m"><input className="tech-input" type="number" value={form.resolution} onChange={(e) => setForm({ ...form, resolution: e.target.value })} /></FormRow>
            <FormRow label="开始时间"><input className="tech-input" type="datetime-local" value={form.startTime} onChange={(e) => setForm({ ...form, startTime: e.target.value })} /></FormRow>
            <FormRow label="结束时间"><input className="tech-input" type="datetime-local" value={form.endTime} onChange={(e) => setForm({ ...form, endTime: e.target.value })} /></FormRow>
            <FormRow label="周期（分）"><input className="tech-input" type="number" value={form.cycle} onChange={(e) => setForm({ ...form, cycle: e.target.value })} /></FormRow>
            <FormRow label="云层厚度"><input className="tech-input" type="number" value={form.cloudThickness} onChange={(e) => setForm({ ...form, cloudThickness: e.target.value })} /></FormRow>
            <FormRow label="定时时间（可选）"><input className="tech-input" type="datetime-local" value={form.appointTime} onChange={(e) => setForm({ ...form, appointTime: e.target.value })} /></FormRow>
            <div className="col-span-2 md:col-span-4">
              <FormRow label={`目标坐标（纬度, 经度）${isMultiCoord ? '：至少 3 个点' : ''}`}>
                <div className="space-y-1.5">
                  {coords.map((c, i) => (
                    <div key={i} className="flex items-center gap-1.5">
                      <input className="tech-input w-full" type="number" placeholder="纬度（-90 ~ 90）" value={c.lat} onChange={(e) => setCoord(i, 'lat', e.target.value)} />
                      <input className="tech-input w-full" type="number" placeholder="经度（-180 ~ 180）" value={c.lon} onChange={(e) => setCoord(i, 'lon', e.target.value)} />
                      {isMultiCoord && (
                        <button className="tech-btn-ghost shrink-0 !px-2" disabled={form.coords.length <= 1} onClick={() => setForm({ ...form, coords: form.coords.filter((_, j) => j !== i) })}>✕</button>
                      )}
                    </div>
                  ))}
                  {isMultiCoord && (
                    <button className="tech-btn-ghost" onClick={() => setForm({ ...form, coords: [...form.coords, { lat: '', lon: '' }] })}>＋新增坐标点</button>
                  )}
                </div>
              </FormRow>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <button className="tech-btn" onClick={submitTask}>提交任务</button>
            {submitMsg && <span className={`text-xs ${submitMsg.startsWith('✓') ? 'text-[#4fe3a5]' : 'text-[#ff8d8d]'}`}>{submitMsg}</span>}
          </div>
        </Panel>

        {/* 规划参数 */}
        <Panel title="规划参数设置" sub="PLANNING PARAMETERS">
          <div className="space-y-3">
            <FormRow label="规划算法">
              <select className="tech-input" value={params.algo} onChange={(e) => setParams({ ...params, algo: e.target.value })}>
                {['蚁群算法', '遗传算法', '贪心算法', '当前方案'].map((a) => <option key={a}>{a}</option>)}
              </select>
            </FormRow>
            <FormRow label="规划周期 s"><input className="tech-input" value={params.period} onChange={(e) => setParams({ ...params, period: e.target.value })} /></FormRow>
            <FormRow label="时间窗粒度 min"><input className="tech-input" value={params.window} onChange={(e) => setParams({ ...params, window: e.target.value })} /></FormRow>
            <FormRow label="最大规划时长 s"><input className="tech-input" value={params.maxTime} onChange={(e) => setParams({ ...params, maxTime: e.target.value })} /></FormRow>
            <FormRow label="任务合并阈值"><input className="tech-input" value={params.mergeThreshold} onChange={(e) => setParams({ ...params, mergeThreshold: e.target.value })} /></FormRow>
            <FormRow label="紧急任务抢占">
              <select className="tech-input" value={params.preempt} onChange={(e) => setParams({ ...params, preempt: e.target.value })}><option>开启</option><option>关闭</option></select>
            </FormRow>
            <div className="flex items-center gap-2 pt-2">
              <button className="tech-btn flex-1" onClick={handleSave}>保存配置</button>
              <button className="tech-btn-ghost" onClick={handleReset}>恢复默认</button>
            </div>
            {saved && <div className="text-center text-xs text-[#4fe3a5]">✓ 已保存到本地（后端暂不支持规划参数下发）</div>}
          </div>
        </Panel>

        {/* 评估结果 */}
        <div className="xl:col-span-2 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <Panel bodyClassName="text-center !py-4">
              <div className="text-[10px] tracking-widest text-[#5f83a8]">任务满足率</div>
              <div className="glow-text num-font mt-1 text-3xl font-bold">{evalData?.satisfactionRate ?? '--'}<span className="text-sm">%</span></div>
            </Panel>
            <Panel bodyClassName="text-center !py-4">
              <div className="text-[10px] tracking-widest text-[#5f83a8]">平均规划耗时</div>
              <div className="glow-text num-font mt-1 text-3xl font-bold">{evalData?.planningTime ?? '--'}<span className="text-sm">s</span></div>
            </Panel>
            <Panel bodyClassName="text-center !py-4">
              <div className="text-[10px] tracking-widest text-[#5f83a8]">当前算法</div>
              <div className="glow-text mt-1 text-xl font-bold">{params.algo}</div>
            </Panel>
          </div>
          <Panel title="任务满足率趋势" sub="SATISFACTION TREND" bodyClassName="!p-1">
            <Chart height={210} option={trendOption} />
          </Panel>
          <Panel title="任务状态分布" sub="TASK STATUS" bodyClassName="!p-1">
            <Chart height={190} option={statsOption} />
          </Panel>
        </div>
      </div>
    </div>
  )
}
