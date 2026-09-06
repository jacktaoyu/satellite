import { useEffect, useMemo, useState } from 'react'
import { Download, RefreshCw, Upload } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { PageHeader, Pagination, Tag, sensorTone, taskStatusTone, Modal, Progress, FormRow, Switch } from '@/components/ui/widgets'
import { getNewTasks, getOldTasks, startTask, pauseTask, manualEndTask, deleteTask, exportTask, addTasks, saveTask, getAllClustersNames } from '@/api'
import type { Task } from '@/api'

const TASK_TYPES = ['点目标', '区域目标', '广域目标', '移动目标', '静态观测', '周期观测']
const SENSOR_TYPES = ['光学', 'SAR', '红外']

interface CoordPoint { lat: string; lon: string }

/** 解析 region 字符串 '[(lat, lon), ...]' / '(lat, lon)' 为坐标点数组，解析失败给一个空点 */
function parseCoords(region?: string): CoordPoint[] {
  const pts: CoordPoint[] = []
  const re = /\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)/g
  let m: RegExpExecArray | null
  while (region && (m = re.exec(region))) pts.push({ lat: m[1], lon: m[2] })
  return pts.length ? pts : [{ lat: '', lon: '' }]
}

/** datetime-local 值 ↔ 后端 'YYYY-MM-DD HH:mm:ss' */
const toLocalInput = (s?: string) => (s ? s.replace(' ', 'T').slice(0, 16) : '')
const toBackendTime = (s: string) => (s ? `${s.replace('T', ' ')}${s.length === 16 ? ':00' : ''}` : '')

interface EditForm {
  id: number
  name: string
  type: string
  priority: number
  emergency: boolean
  sensorType: string
  resolution: string
  startTime: string
  endTime: string
  cycle: string
  cloudThickness: string
  cluster: string
  coords: CoordPoint[]
}

/** 坐标编辑控件：每点一行（纬度/经度 + 删除），底部新增按钮 */
function CoordEditor({ coords, onChange }: { coords: CoordPoint[]; onChange: (c: CoordPoint[]) => void }) {
  const set = (i: number, k: keyof CoordPoint, v: string) => onChange(coords.map((c, j) => (j === i ? { ...c, [k]: v } : c)))
  return (
    <div className="space-y-1.5">
      {coords.map((c, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <input className="tech-input w-full" type="number" placeholder="纬度" value={c.lat} onChange={(e) => set(i, 'lat', e.target.value)} />
          <input className="tech-input w-full" type="number" placeholder="经度" value={c.lon} onChange={(e) => set(i, 'lon', e.target.value)} />
          <button className="tech-btn-ghost shrink-0 !px-2" disabled={coords.length <= 1} onClick={() => onChange(coords.filter((_, j) => j !== i))}>✕</button>
        </div>
      ))}
      <button className="tech-btn-ghost w-full" onClick={() => onChange([...coords, { lat: '', lon: '' }])}>＋新增坐标点</button>
    </div>
  )
}

export default function TaskAttribute() {
  const [tab, setTab] = useState<'new' | 'old'>('new')
  const [list, setList] = useState<Task[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [query, setQuery] = useState({ name: '', type: '', status: '' })
  const [detail, setDetail] = useState<Task | null>(null)
  const [edit, setEdit] = useState<EditForm | null>(null)
  const [editMsg, setEditMsg] = useState('')
  const [clusters, setClusters] = useState<string[]>([])

  useEffect(() => { getAllClustersNames().then(setClusters) }, [])

  const openEdit = (t: Task) => {
    setEditMsg('')
    setEdit({
      id: t.id,
      name: t.name,
      type: t.type,
      priority: t.priority || 1,
      emergency: t.emergency,
      sensorType: t.sensorType,
      resolution: t.resolution ? String(t.resolution) : '',
      startTime: toLocalInput(t.startTime),
      endTime: toLocalInput(t.endTime),
      cycle: '',
      cloudThickness: '',
      cluster: t.cluster ?? '',
      coords: parseCoords(t.region),
    })
  }

  const saveEdit = async () => {
    if (!edit) return
    const coordinates = edit.coords.filter((c) => c.lat !== '' && c.lon !== '').map((c) => `${c.lat},${c.lon}`)
    const r = await saveTask({
      id: edit.id,
      name: edit.name,
      type: edit.type,
      priority: edit.priority,
      emergency: edit.emergency,
      sensorType: edit.sensorType || undefined,
      resolution: edit.resolution ? Number(edit.resolution) : undefined,
      startTime: toBackendTime(edit.startTime) || undefined,
      endTime: toBackendTime(edit.endTime) || undefined,
      cycle: edit.cycle || undefined,
      cloudThickness: edit.cloudThickness ? Number(edit.cloudThickness) : undefined,
      cluster: edit.cluster || undefined,
      coordinates,
    })
    if (r?.code === 200) { setEdit(null); load() } else setEditMsg(r?.msg ?? '保存失败')
  }

  const load = async () => {
    // GET /tasks/getNewTasks | getOldTasks
    setList(tab === 'new' ? await getNewTasks() : await getOldTasks())
  }
  useEffect(() => { load() }, [tab])

  const filtered = useMemo(() => list.filter((t) =>
    (!query.name || t.name.includes(query.name)) &&
    (!query.type || t.type === query.type) &&
    (!query.status || t.status === query.status),
  ), [list, query])
  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize)

  const op = async (fn: (id: number) => Promise<unknown>, id: number) => { await fn(id); load() }

  const upload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) addTasks(f).then(load) // POST /tasks/addTasks
    e.target.value = ''
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader
        title="任务属性"
        sub="TASK ATTRIBUTE"
        right={
          <>
            <label className="tech-btn flex cursor-pointer items-center gap-1">
              <Upload size={12} />批量导入<input type="file" accept=".txt,.csv,.json" className="hidden" onChange={upload} />
            </label>
            <button className="tech-btn-ghost flex items-center gap-1" onClick={() => exportTask()}><Download size={12} />导出任务</button>
            <button className="tech-btn-ghost flex items-center gap-1" onClick={load}><RefreshCw size={12} />刷新</button>
          </>
        }
      />

      {/* Tab + 搜索 */}
      <Panel className="mb-3 shrink-0" bodyClassName="flex flex-wrap items-center gap-2 !py-2.5">
        <div className="mr-4 flex gap-1 rounded border border-[rgba(0,220,255,0.25)] p-0.5">
          {(['new', 'old'] as const).map((k) => (
            <button
              key={k}
              className={`rounded px-4 py-1 text-xs transition ${tab === k ? 'bg-[rgba(0,220,255,0.18)] text-[#4fd8ff]' : 'text-[#6b93b8] hover:text-[#a8cbe8]'}`}
              onClick={() => { setTab(k); setPage(1) }}
            >
              {k === 'new' ? '新任务' : '旧任务'}
            </button>
          ))}
        </div>
        <input className="tech-input w-40" placeholder="任务名称" value={query.name} onChange={(e) => { setQuery({ ...query, name: e.target.value }); setPage(1) }} />
        <select className="tech-input w-32" value={query.type} onChange={(e) => { setQuery({ ...query, type: e.target.value }); setPage(1) }}>
          <option value="">任务类型（全部）</option>
          {['点目标', '区域目标', '广域目标', '移动目标', '静态观测', '周期观测'].map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="tech-input w-32" value={query.status} onChange={(e) => { setQuery({ ...query, status: e.target.value }); setPage(1) }}>
          <option value="">状态（全部）</option>
          {['等待执行', '执行中', '暂停', '已完成'].map((t) => <option key={t}>{t}</option>)}
        </select>
        <button className="tech-btn">搜索</button>
        <button className="tech-btn-ghost" onClick={() => { setQuery({ name: '', type: '', status: '' }); setPage(1) }}>重置</button>
      </Panel>

      {/* 表格 */}
      <Panel bodyClassName="!p-0">
        <div className="overflow-x-auto">
        <table className="tech-table">
          <thead>
            <tr>
              <th>ID</th><th>任务名称</th><th>类型</th><th>优先级</th><th>载荷</th><th>分辨率</th><th>区域</th><th>所属卫星</th><th>所属星簇</th><th>状态</th><th>执行进度</th><th>计划窗口</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            {pageData.map((t) => (
              <tr key={t.id}>
                <td className="num-font">{t.id}</td>
                <td>
                  <span className="text-[#4fd8ff]">{t.name}</span>
                  {t.emergency && <span className="ml-1.5 inline-block rounded-sm bg-[rgba(255,180,60,0.15)] px-1 py-px text-[9px] text-[#ffb43c]">紧急</span>}
                </td>
                <td>{t.type}</td>
                <td className="num-font">{t.priority}</td>
                <td><Tag text={t.sensorType} tone={sensorTone(t.sensorType)} /></td>
                <td className="num-font">{t.resolution ? `${t.resolution} m` : '—'}</td>
                <td className="max-w-36 truncate text-[11px]" title={t.region}>{t.region ?? '—'}</td>
                <td>{t.satellite ?? '—'}</td>
                <td>{t.cluster ?? '—'}</td>
                <td><Tag text={t.status} tone={taskStatusTone(t.status)} /></td>
                <td className="w-32">
                  {t.progress != null
                    ? <Progress value={t.progress} color={t.emergency ? '#ffb43c' : '#00dcff'} />
                    : <span className="text-[#5f83a8]">—</span>}
                </td>
                <td className="num-font text-[11px]">{t.scheduledTime ?? `${t.startTime} ~ ${t.endTime}`}</td>
                <td className="whitespace-nowrap">
                  <a className="table-link" onClick={() => setDetail(t)}>详情</a>
                  {t.status !== '执行中' && <a className="table-link" onClick={() => openEdit(t)}>编辑</a>}
                  {t.status === '等待执行' && <a className="table-link" onClick={() => op(startTask, t.id)}>启动</a>}
                  {t.status === '执行中' && (
                    <>
                      <a className="table-link" onClick={() => op(pauseTask, t.id)}>暂停</a>
                      <a className="table-link" onClick={() => op(manualEndTask, t.id)}>手动结束</a>
                    </>
                  )}
                  {t.status === '暂停' && <a className="table-link" onClick={() => op(startTask, t.id)}>继续</a>}
                  <a className="table-link" onClick={() => exportTask(t.id)}>导出</a>
                  <a className="table-link !text-[#ff7a7a]" onClick={() => op(deleteTask, t.id)}>删除</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        <div className="px-3 pb-2">
          <Pagination page={page} total={filtered.length} pageSize={pageSize} onChange={setPage} onPageSizeChange={(n) => { setPageSize(n); setPage(1) }} />
        </div>
      </Panel>

      {/* 详情弹窗 */}
      <Modal title="任务详情" open={!!detail} onClose={() => setDetail(null)} width={560}>
        {detail && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
            {([
              ['任务编号', detail.id], ['任务名称', detail.name], ['任务类型', detail.type], ['优先级', detail.priority],
              ['是否紧急', detail.emergency ? '是' : '否'], ['载荷类型', detail.sensorType], ['分辨率', `${detail.resolution} m`],
              ['所属卫星', detail.satellite ?? '—'], ['所属星簇', detail.cluster ?? '—'], ['当前状态', detail.status],
              ['开始时间', detail.startTime], ['结束时间', detail.endTime], ['目标区域', detail.region ?? '—'], ['执行进度', detail.progress != null ? `${detail.progress}%` : '—'],
            ] as [string, string | number][]).map(([label, v]) => (
              <div key={label} className="desc-item"><span className="label">{label}</span><span className="value num-font">{v}</span></div>
            ))}
          </div>
        )}
      </Modal>

      {/* 编辑弹窗（执行中任务后端返回 409，入口已在操作列隐藏） */}
      <Modal
        title="编辑任务"
        open={!!edit}
        onClose={() => setEdit(null)}
        width={640}
        footer={
          <>
            {editMsg && <span className="mr-auto text-xs text-[#ff7a7a]">{editMsg}</span>}
            <button className="tech-btn-ghost" onClick={() => setEdit(null)}>取消</button>
            <button className="tech-btn" onClick={saveEdit}>保存</button>
          </>
        }
      >
        {edit && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <FormRow label="任务名称"><input className="tech-input" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></FormRow>
              <FormRow label="任务类型">
                <select className="tech-input" value={edit.type} onChange={(e) => setEdit({ ...edit, type: e.target.value })}>
                  {TASK_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </FormRow>
              <FormRow label="优先级（1-5）"><input className="tech-input" type="number" min={1} max={5} value={edit.priority} onChange={(e) => setEdit({ ...edit, priority: Math.max(1, Math.min(5, +e.target.value || 1)) })} /></FormRow>
              <FormRow label="是否紧急"><Switch checked={edit.emergency} onChange={(v) => setEdit({ ...edit, emergency: v })} /></FormRow>
              <FormRow label="载荷类型">
                <select className="tech-input" value={edit.sensorType} onChange={(e) => setEdit({ ...edit, sensorType: e.target.value })}>
                  {SENSOR_TYPES.map((s) => <option key={s}>{s}</option>)}
                </select>
              </FormRow>
              <FormRow label="分辨率 m"><input className="tech-input" type="number" step="0.1" value={edit.resolution} onChange={(e) => setEdit({ ...edit, resolution: e.target.value })} /></FormRow>
              <FormRow label="开始时间"><input className="tech-input" type="datetime-local" value={edit.startTime} onChange={(e) => setEdit({ ...edit, startTime: e.target.value })} /></FormRow>
              <FormRow label="结束时间"><input className="tech-input" type="datetime-local" value={edit.endTime} onChange={(e) => setEdit({ ...edit, endTime: e.target.value })} /></FormRow>
              <FormRow label="周期（分）"><input className="tech-input" type="number" value={edit.cycle} onChange={(e) => setEdit({ ...edit, cycle: e.target.value })} /></FormRow>
              <FormRow label="云层厚度 m"><input className="tech-input" type="number" value={edit.cloudThickness} onChange={(e) => setEdit({ ...edit, cloudThickness: e.target.value })} /></FormRow>
              <FormRow label="所属星簇">
                <select className="tech-input" value={edit.cluster} onChange={(e) => setEdit({ ...edit, cluster: e.target.value })}>
                  <option value="">不指定</option>
                  {clusters.map((c) => <option key={c}>{c}</option>)}
                </select>
              </FormRow>
            </div>
            <FormRow label="目标坐标（纬度/经度）">
              <CoordEditor coords={edit.coords} onChange={(coords) => setEdit({ ...edit, coords })} />
            </FormRow>
          </div>
        )}
      </Modal>
    </div>
  )
}
