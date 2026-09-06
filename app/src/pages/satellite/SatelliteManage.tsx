import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { Download, RefreshCw } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { PageHeader, Modal, FormRow, Pagination, Tag, sensorTone } from '@/components/ui/widgets'
import { getAllSatellites, getSatelliteByName, setSatelliteAvailable, setSatelliteProperty, exportSatelliteInfo } from '@/api'
import type { Satellite } from '@/api'

export default function SatelliteManage() {
  const navigate = useNavigate()
  const [list, setList] = useState<Satellite[]>([])
  const [query, setQuery] = useState({ name: '', sensor: '', status: '' })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [sort, setSort] = useState<{ key: 'battery' | 'storage'; desc: boolean } | null>(null)
  const [editTarget, setEditTarget] = useState<Satellite | null>(null)
  const [form, setForm] = useState<Record<string, string>>({})

  const load = () => getAllSatellites().then(setList) // POST /satellites/getAllSatellites
  useEffect(() => { load() }, [])

  const filtered = useMemo(() => {
    let r = list.filter((s) =>
      (!query.name || s.name.includes(query.name)) &&
      (!query.sensor || s.sensorType === query.sensor) &&
      (!query.status || (query.status === '可用' ? s.available : !s.available)),
    )
    if (sort) r = [...r].sort((a, b) => (sort.desc ? b[sort.key] - a[sort.key] : a[sort.key] - b[sort.key]))
    return r
  }, [list, query, sort])

  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize)

  const toggleAll = () => {
    setSelected(selected.size === pageData.length ? new Set() : new Set(pageData.map((s) => s.id)))
  }

  const batchSet = async (available: boolean) => {
    // POST /satellites/setSatelliteAvailable/{id} × N
    await Promise.all([...selected].map((id) => setSatelliteAvailable(id, available)))
    setSelected(new Set())
    load()
  }

  const openEdit = async (s: Satellite) => {
    setEditTarget(s)
    // 列表是批量接口（缺功率/载荷等字段），编辑时拉取单星详情接口回填真实参数
    const d = (await getSatelliteByName(s.name).catch(() => undefined)) ?? s
    setForm({
      storage: String(d.storage), battery: String(d.battery), downlinkRate: String(d.downlinkRate),
      idle: String(d.power.idle), solar: String(d.power.solar), maneuver: String(d.power.maneuver), imaging: String(d.power.imaging),
      rotateSpeed: String(d.payload.rotateSpeed), stableTime: String(d.payload.stableTime),
      maxRoll: String(d.payload.maxRoll), maxPitch: String(d.payload.maxPitch), cloudThreshold: String(d.payload.cloudThreshold),
    })
  }

  const saveEdit = async () => {
    if (!editTarget) return
    // POST /satellites/setSatelliteProperty/{id}
    await setSatelliteProperty(editTarget.id, form)
    setEditTarget(null)
    load()
  }

  const SortTh = ({ label, k }: { label: string; k: 'battery' | 'storage' }) => (
    <th className="cursor-pointer select-none" onClick={() => setSort(sort?.key === k ? { key: k, desc: !sort.desc } : { key: k, desc: true })}>
      {label} {sort?.key === k ? (sort.desc ? '↓' : '↑') : '⇅'}
    </th>
  )

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader
        title="卫星管理"
        sub="SATELLITE MANAGEMENT"
        right={
          <>
            <button className="tech-btn-ghost flex items-center gap-1" onClick={() => exportSatelliteInfo()}><Download size={12} />导出全部</button>
            <button className="tech-btn-ghost flex items-center gap-1" onClick={load}><RefreshCw size={12} />刷新</button>
          </>
        }
      />

      {/* 搜索工具栏 */}
      <Panel className="mb-3 shrink-0" bodyClassName="!py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <input className="tech-input w-40" placeholder="卫星名称" value={query.name} onChange={(e) => { setQuery({ ...query, name: e.target.value }); setPage(1) }} />
          <select className="tech-input w-32" value={query.sensor} onChange={(e) => { setQuery({ ...query, sensor: e.target.value }); setPage(1) }}>
            <option value="">载荷类型（全部）</option><option>光学</option><option>SAR</option><option>红外</option>
          </select>
          <select className="tech-input w-32" value={query.status} onChange={(e) => { setQuery({ ...query, status: e.target.value }); setPage(1) }}>
            <option value="">状态（全部）</option><option>可用</option><option>不可用</option>
          </select>
          <button className="tech-btn">搜索</button>
          <button className="tech-btn-ghost" onClick={() => { setQuery({ name: '', sensor: '', status: '' }); setPage(1) }}>重置</button>
        </div>
      </Panel>

      {/* 批量操作栏 */}
      {selected.size > 0 && (
        <Panel className="mb-3 shrink-0" bodyClassName="flex items-center gap-3 !py-2">
          <span className="text-xs text-[#4fd8ff]">已选择 {selected.size} 颗卫星</span>
          <button className="tech-btn" onClick={() => batchSet(true)}>批量启用</button>
          <button className="tech-btn-ghost" onClick={() => batchSet(false)}>批量禁用</button>
          <button className="tech-btn-ghost" onClick={() => exportSatelliteInfo()}>批量导出</button>
          <button className="tech-btn-ghost ml-auto" onClick={() => setSelected(new Set())}>清空选择</button>
        </Panel>
      )}

      {/* 表格 */}
      <Panel bodyClassName="!p-0">
        <table className="tech-table">
          <thead>
            <tr>
              <th className="w-8"><input type="checkbox" className="accent-[#00dcff]" checked={pageData.length > 0 && selected.size === pageData.length} onChange={toggleAll} /></th>
              <th>ID</th><th>卫星名称</th><th>轨道</th><th>载荷</th>
              <SortTh label="电池 Wh" k="battery" />
              <SortTh label="存储 GB" k="storage" />
              <th>分辨率 m</th><th>状态</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            {pageData.map((s) => (
              <tr key={s.id}>
                <td>
                  <input type="checkbox" className="accent-[#00dcff]" checked={selected.has(s.id)}
                    onChange={() => setSelected((prev) => { const n = new Set(prev); n.has(s.id) ? n.delete(s.id) : n.add(s.id); return n })} />
                </td>
                <td className="num-font">{s.id}</td>
                <td className="text-[#4fd8ff]">{s.name}</td>
                <td>{s.orbit}</td>
                <td><Tag text={s.sensorType} tone={sensorTone(s.sensorType)} /></td>
                <td className={`num-font ${s.battery < 20 ? 'text-[#ff7a7a]' : ''}`}>{s.battery}</td>
                <td className="num-font">{s.storage}</td>
                <td className="num-font">{s.resolution}</td>
                <td><Tag text={s.available ? '可用' : '不可用'} tone={s.available ? 'green' : 'gray'} /></td>
                <td>
                  <a className="table-link" onClick={() => navigate(`/satellite/Weixing/info/${encodeURIComponent(s.name)}`)}>详情</a>
                  <a className="table-link" onClick={() => openEdit(s)}>编辑</a>
                  <a className="table-link" onClick={() => exportSatelliteInfo(s.id)}>导出</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-3 pb-2">
          <Pagination page={page} total={filtered.length} pageSize={pageSize} onChange={setPage} onPageSizeChange={(n) => { setPageSize(n); setPage(1) }} />
        </div>
      </Panel>

      {/* 编辑弹窗 */}
      <Modal
        title="编辑卫星参数"
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        width={640}
        footer={
          <>
            <button className="tech-btn-ghost" onClick={() => setEditTarget(null)}>取消</button>
            <button className="tech-btn" onClick={saveEdit}>保存</button>
          </>
        }
      >
        {editTarget && (
          <div className="space-y-4">
            <div>
              <div className="panel-title mb-2">基础参数</div>
              <div className="grid grid-cols-3 gap-3">
                <FormRow label="存储容量 GB"><input className="tech-input" value={form.storage} onChange={(e) => setForm({ ...form, storage: e.target.value })} /></FormRow>
                <FormRow label="电池容量 Wh"><input className="tech-input" value={form.battery} onChange={(e) => setForm({ ...form, battery: e.target.value })} /></FormRow>
                <FormRow label="下行速率 GB/s"><input className="tech-input" value={form.downlinkRate} onChange={(e) => setForm({ ...form, downlinkRate: e.target.value })} /></FormRow>
              </div>
            </div>
            <div>
              <div className="panel-title mb-2">功率参数</div>
              <div className="grid grid-cols-4 gap-3">
                <FormRow label="空闲功率 W"><input className="tech-input" value={form.idle} onChange={(e) => setForm({ ...form, idle: e.target.value })} /></FormRow>
                <FormRow label="太阳能功率 W"><input className="tech-input" value={form.solar} onChange={(e) => setForm({ ...form, solar: e.target.value })} /></FormRow>
                <FormRow label="机动功率 W"><input className="tech-input" value={form.maneuver} onChange={(e) => setForm({ ...form, maneuver: e.target.value })} /></FormRow>
                <FormRow label="成像功率 W"><input className="tech-input" value={form.imaging} onChange={(e) => setForm({ ...form, imaging: e.target.value })} /></FormRow>
              </div>
            </div>
            <div>
              <div className="panel-title mb-2">载荷参数</div>
              <div className="grid grid-cols-3 gap-3">
                <FormRow label="角度转动速度 °/s"><input className="tech-input" value={form.rotateSpeed} onChange={(e) => setForm({ ...form, rotateSpeed: e.target.value })} /></FormRow>
                <FormRow label="稳定时间 s"><input className="tech-input" value={form.stableTime} onChange={(e) => setForm({ ...form, stableTime: e.target.value })} /></FormRow>
                <FormRow label="最大侧摆角度 °"><input className="tech-input" value={form.maxRoll} onChange={(e) => setForm({ ...form, maxRoll: e.target.value })} /></FormRow>
                <FormRow label="最大俯仰角度 °"><input className="tech-input" value={form.maxPitch} onChange={(e) => setForm({ ...form, maxPitch: e.target.value })} /></FormRow>
                <FormRow label="云层厚度阈值 m"><input className="tech-input" value={form.cloudThreshold} onChange={(e) => setForm({ ...form, cloudThreshold: e.target.value })} /></FormRow>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
