import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Upload, Download } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { PageHeader, FormRow, Switch } from '@/components/ui/widgets'
import {
  getSubmitStatus,
  saveSimParameters,
  saveSimConfig,
  getAutoRun,
  changeAutoRun,
  getModel,
  setModel,
  getConstraintConfig,
  saveConstraintConfig,
  initTLE,
  initFiles,
  exportTleFile,
} from '@/api'
import type { ConstraintItem } from '@/api'

const MODEL_OPTIONS = [
  { value: 0, label: '综合最优方案' },
  { value: 1, label: '任务满足率最优' },
  { value: 2, label: '资源利用率最大' },
  { value: 3, label: '成像质量最高' },
]

/** datetime-local 值 'YYYY-MM-DDTHH:mm' → 'YYYY-MM-DD HH:mm:ss' */
const toLocalTimeStr = (v: string) => {
  const s = v.replace('T', ' ')
  return v.length === 16 ? `${s}:00` : s
}

export default function SystemSettings() {
  const navigate = useNavigate()
  const [speed, setSpeed] = useState(12)
  const [auto, setAuto] = useState(true)
  const [startTime, setStartTime] = useState('2025-06-06T00:00')
  const [endTime, setEndTime] = useState('2025-06-13T00:00')
  const [completed, setCompleted] = useState(1.0)
  const [balance, setBalance] = useState(1.0)
  const [priority, setPriority] = useState(1.0)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [submitStatus, setSubmitStatus] = useState<any>(null)
  const [autoRun, setAutoRun] = useState(true)
  const [model, setModelState] = useState(0)
  const [modeError, setModeError] = useState('')
  const [constraints, setConstraints] = useState<ConstraintItem[]>([])
  const [constraintSaved, setConstraintSaved] = useState(false)
  const [constraintError, setConstraintError] = useState('')

  useEffect(() => {
    getSubmitStatus().then(setSubmitStatus) // GET /getSubmitStatus
    getAutoRun().then(setAutoRun) // GET /getAutoRun
    getModel().then((r) => {
      setModelState(r.mode)
      if (typeof r.auto === 'boolean') setAutoRun(r.auto)
    }) // GET /getModel
    getConstraintConfig().then(setConstraints) // GET /constraintConfig
  }, [])

  const save = async () => {
    setSaveError('')
    setSaved(false)
    const r1 = await saveSimConfig({
      startTime: toLocalTimeStr(startTime),
      endTime: toLocalTimeStr(endTime),
      completed,
      balance,
      priority,
    }) // POST /simulateParameters
    if (r1.code !== 200) {
      setSaveError(r1.msg || '仿真参数提交失败')
      return
    }
    const r2 = await saveSimParameters({ speed, auto }) // POST /saveSimParameters（时间倍率）
    if (r2.code !== 200) {
      setSaveError(r2.msg || '时间倍率提交失败')
      return
    }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const toggleAutoRun = async (v: boolean) => {
    if (v === autoRun) return
    const prev = autoRun
    setAutoRun(v)
    setModeError('')
    const r = await changeAutoRun(v) // POST /changeAutoRun
    if (r.code !== 200) {
      setAutoRun(prev) // 失败回滚
      setModeError(r.msg || '运行模式切换失败')
    }
  }

  const selectModel = async (v: number) => {
    if (v === model) return
    const prev = model
    setModelState(v)
    setModeError('')
    const r = await setModel(v) // POST /changeModel
    if (r.code !== 200) {
      setModelState(prev) // 失败回滚
      setModeError(r.msg || '方案切换失败')
    }
  }

  const updateConstraint = (key: ConstraintItem['key'], patch: Partial<ConstraintItem>) => {
    setConstraints((list) => list.map((c) => (c.key === key ? { ...c, ...patch } : c)))
  }

  const saveConstraints = async () => {
    setConstraintError('')
    setConstraintSaved(false)
    const r = await saveConstraintConfig(constraints.map(({ key, enabled, threshold }) => ({ key, enabled, threshold }))) // POST /constraintConfig
    if (r.code !== 200) {
      setConstraintError(r.msg || '约束配置保存失败')
      return
    }
    setConstraintSaved(true)
    setTimeout(() => setConstraintSaved(false), 2000)
  }

  const upload = (fn: (f: File) => Promise<unknown>) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) fn(f)
    e.target.value = ''
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader title="系统设置" sub="SYSTEM SETTINGS" />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        {/* 仿真参数 */}
        <Panel title="仿真参数" sub="SIMULATION">
          <div className="space-y-3">
            <FormRow label="仿真起始时间">
              <input className="tech-input" type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
            </FormRow>
            <FormRow label="仿真结束时间">
              <input className="tech-input" type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
            </FormRow>
            <FormRow label="时间倍率">
              <div className="flex items-center gap-3">
                <input type="range" min={1} max={100} value={speed} onChange={(e) => setSpeed(+e.target.value)} className="w-full accent-[#00dcff]" />
                <span className="num-font w-14 text-right text-[#4fd8ff]">×{speed}</span>
              </div>
            </FormRow>
            <FormRow label="任务完成率权重">
              <input className="tech-input" type="number" step={0.1} value={completed} onChange={(e) => setCompleted(+e.target.value)} />
            </FormRow>
            <FormRow label="负载均衡权重">
              <input className="tech-input" type="number" step={0.1} value={balance} onChange={(e) => setBalance(+e.target.value)} />
            </FormRow>
            <FormRow label="优先级权重">
              <input className="tech-input" type="number" step={0.1} value={priority} onChange={(e) => setPriority(+e.target.value)} />
            </FormRow>
            <FormRow label="自动推进时钟"><Switch checked={auto} onChange={setAuto} /></FormRow>
            <div className="flex items-center gap-2 pt-2">
              <button className="tech-btn flex-1" onClick={save}>保存参数</button>
              {saved && <span className="text-xs text-[#4fe3a5]">✓ 已保存</span>}
              {saveError && <span className="text-xs text-[#ff8d8d]">{saveError}</span>}
            </div>
          </div>
        </Panel>

        {/* 数据初始化 */}
        <Panel title="数据初始化" sub="DATA INITIALIZATION">
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded border border-[rgba(0,220,255,0.15)] bg-[rgba(0,220,255,0.04)] p-3">
              <div>
                <div className="text-xs font-semibold text-[#c2e4ff]">TLE 轨道根数</div>
                <div className="mt-0.5 text-[10px] text-[#5f83a8]">上传两行根数文件，重建全星座轨道</div>
              </div>
              <div className="flex gap-2">
                <label className="tech-btn flex cursor-pointer items-center gap-1"><Upload size={11} />上传<input type="file" accept=".txt,.tle" className="hidden" onChange={upload(initTLE)} /></label>
                <button className="tech-btn-ghost flex items-center gap-1" onClick={() => exportTleFile()}><Download size={11} />导出</button>
              </div>
            </div>
            <div className="flex items-center justify-between rounded border border-[rgba(0,220,255,0.15)] bg-[rgba(0,220,255,0.04)] p-3">
              <div>
                <div className="text-xs font-semibold text-[#c2e4ff]">系统配置文件</div>
                <div className="mt-0.5 text-[10px] text-[#5f83a8]">批量导入卫星 / 任务 / 星簇初始化数据</div>
              </div>
              <label className="tech-btn flex cursor-pointer items-center gap-1"><Upload size={11} />上传<input type="file" accept=".json,.zip" className="hidden" onChange={upload(initFiles)} /></label>
            </div>
            <div className="flex items-center justify-between rounded border border-[rgba(0,220,255,0.15)] bg-[rgba(0,220,255,0.04)] p-3">
              <div>
                <div className="text-xs font-semibold text-[#c2e4ff]">载荷网络参数</div>
                <div className="mt-0.5 text-[10px] text-[#5f83a8]">按载荷类型批量设置成像与链路参数</div>
              </div>
              <button className="tech-btn" onClick={() => navigate('/satellite/network_parameters')}>进入设置</button>
            </div>
          </div>
        </Panel>

        {/* 运行模式与方案 */}
        <Panel title="运行模式与方案" sub="RUN MODE & PLAN">
          <div className="space-y-3">
            <FormRow label="运行模式">
              <div className="flex gap-2">
                <button
                  className={autoRun ? 'tech-btn flex-1' : 'tech-btn-ghost flex-1'}
                  onClick={() => toggleAutoRun(true)}
                >
                  自主运行
                </button>
                <button
                  className={!autoRun ? 'tech-btn flex-1' : 'tech-btn-ghost flex-1'}
                  onClick={() => toggleAutoRun(false)}
                >
                  程序控制
                </button>
              </div>
            </FormRow>
            <div className="text-[10px] text-[#5f83a8]">
              {autoRun ? '自主运行：系统自动决策，完成方案规划与调度' : '程序控制（手动）：允许直接指定优化目标方案'}
            </div>
            <FormRow label="方案选择">
              <div className="grid grid-cols-2 gap-2">
                {MODEL_OPTIONS.map((o) => (
                  <button
                    key={o.value}
                    className={model === o.value ? 'tech-btn' : 'tech-btn-ghost'}
                    onClick={() => selectModel(o.value)}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </FormRow>
            {modeError && <div className="text-xs text-[#ff8d8d]">{modeError}</div>}
          </div>
        </Panel>

        {/* 星簇约束管理 */}
        <Panel title="星簇约束管理" sub="CLUSTER CONSTRAINTS">
          {constraints.length === 0 ? (
            <div className="py-6 text-center text-xs text-[#5f83a8]">约束配置加载失败或为空</div>
          ) : (
            <div className="space-y-3">
              {constraints.map((c) => (
                <div key={c.key} className="flex items-center justify-between gap-3 rounded border border-[rgba(0,220,255,0.15)] bg-[rgba(0,220,255,0.04)] p-3">
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-[#c2e4ff]">{c.name}</div>
                    <div className="mt-0.5 text-[10px] text-[#5f83a8]">{c.desc}</div>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <Switch checked={c.enabled} onChange={(v) => updateConstraint(c.key, { enabled: v })} />
                    <div className="flex items-center gap-1">
                      <input
                        className="tech-input w-24"
                        type="number"
                        step={0.1}
                        value={c.threshold}
                        disabled={!c.enabled}
                        onChange={(e) => updateConstraint(c.key, { threshold: +e.target.value })}
                      />
                      <span className="w-10 text-[10px] text-[#7ea6d8]">{c.unit}</span>
                    </div>
                  </div>
                </div>
              ))}
              <div className="flex items-center gap-2 pt-1">
                <button className="tech-btn flex-1" onClick={saveConstraints}>保存约束</button>
                {constraintSaved && <span className="text-xs text-[#4fe3a5]">✓ 已保存</span>}
                {constraintError && <span className="text-xs text-[#ff8d8d]">{constraintError}</span>}
              </div>
            </div>
          )}
        </Panel>

        {/* 提交状态（真实数据：GET /isSubmitTle、/isSubmitSat、/isSubmitSys，后端仅提供布尔状态） */}
        <Panel title="数据提交状态" sub="SUBMIT STATUS" className="xl:col-span-2" bodyClassName="!p-0">
          <table className="tech-table">
            <thead><tr><th>数据项</th><th>状态</th></tr></thead>
            <tbody>
              {[
                { name: 'TLE 轨道根数', ok: submitStatus?.tle },
                { name: '卫星参数', ok: submitStatus?.sat },
                { name: '系统配置文件', ok: submitStatus?.sys },
              ].map((it) => (
                <tr key={it.name}>
                  <td className="text-[#4fd8ff]">{it.name}</td>
                  <td>
                    {it.ok == null
                      ? <span className="text-[#5f83a8]">● 未知</span>
                      : <span className={it.ok ? 'text-[#4fe3a5]' : 'text-[#ffb43c]'}>{it.ok ? '● 已提交' : '● 未提交'}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  )
}
