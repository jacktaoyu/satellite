import { useEffect, useState } from 'react'
import { Download, Plus, RefreshCw, Upload } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { PageHeader, Modal, FormRow, Tag } from '@/components/ui/widgets'
import { getClustersByPage, getOrbits, getClusterDetailsByName, saveCluster, deleteClusterById, setAvailableCluster, replanCluster, submitClusterFile, exportAllClusters, getOrbitPayloadInfo } from '@/api'
import type { Cluster } from '@/api'

/** 载荷英文键 → 中文标签 */
const PAYLOAD_LABELS: Record<string, string> = { optical: '光学', SAR: 'SAR', infrared: '红外' }
/** payload 字符串键（中/英）→ 英文键 */
const PAYLOAD_KEY_EN: Record<string, string> = { 光学: 'optical', SAR: 'SAR', 红外: 'infrared', optical: 'optical', infrared: 'infrared' }

/** 从轨道显示文本（如「第10轨道光学:0.5|SAR:1」）提取轨道编号 */
const orbitNo = (s: string) => {
  const m = String(s).match(/\d+/)
  return m ? parseInt(m[0], 10) : null
}

/** 解析 payload 字符串（如 'optical:0.5,1|SAR:2' 或 '光学:0.5,1'）为勾选状态 */
const parsePayloadSpec = (spec: string): Record<string, number[]> => {
  const sel: Record<string, number[]> = {}
  for (const part of String(spec ?? '').split('|')) {
    const [k, v] = part.split(':')
    const key = PAYLOAD_KEY_EN[k]
    if (!key) continue
    sel[key] = v ? v.split(',').map(Number).filter((n) => !isNaN(n)) : []
  }
  return sel
}

export default function ClusterManage() {
  const [list, setList] = useState<Cluster[]>([])
  const [orbits, setOrbits] = useState<string[]>([])
  const [editTarget, setEditTarget] = useState<Cluster | null>(null)
  const [creating, setCreating] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [replan, setReplan] = useState<{ open: boolean; from: string; to: string }>({ open: false, from: '', to: '' })
  const [form, setForm] = useState({ name: '', orbit: '' })
  const [payloadOpts, setPayloadOpts] = useState<Record<string, number[]>>({})
  const [payloadSel, setPayloadSel] = useState<Record<string, number[]>>({})

  const load = async () => {
    // GET /clusters/getClustersByPage + /clusters/getOrbits
    const [c, o] = await Promise.all([getClustersByPage(), getOrbits()])
    setList(c)
    setOrbits(o)
  }
  useEffect(() => { load() }, [])

  const openDetail = async (name: string) => setDetail(await getClusterDetailsByName(name)) // POST /clusters/getClusterDetailsByName

  /** 选定轨道后拉取载荷-分辨率选项（POST /clusters/getInfoByOrbits），并按已选状态回填 */
  const loadPayloadOptions = async (orbitText: string, sel: Record<string, number[]> = {}) => {
    const n = orbitNo(orbitText)
    if (n === null) { setPayloadOpts({}); setPayloadSel({}); return }
    const map = await getOrbitPayloadInfo([n])
    setPayloadOpts(map)
    // 仅保留接口返回的载荷键与合法分辨率
    const next: Record<string, number[]> = {}
    for (const k of Object.keys(map)) next[k] = (sel[k] ?? []).filter((r) => map[k].includes(r))
    setPayloadSel(next)
  }

  const toggleRes = (key: string, res: number) => {
    setPayloadSel((prev) => {
      const cur = prev[key] ?? []
      return { ...prev, [key]: cur.includes(res) ? cur.filter((r) => r !== res) : [...cur, res].sort((a, b) => a - b) }
    })
  }

  const openCreate = () => {
    setForm({ name: '', orbit: '' })
    setPayloadOpts({})
    setPayloadSel({})
    setCreating(true)
  }

  const openEdit = (c: Cluster) => {
    setForm({ name: c.name, orbit: c.orbits[0] ?? '' })
    setEditTarget(c)
    loadPayloadOptions(c.orbits[0] ?? '', parsePayloadSpec(c.payloadSpec))
  }

  const save = async () => {
    // 组装 payloadSpec：'英文载荷键:res1,res2|...'（未勾选的载荷为空），由 api 层解析为 payload_resolution
    const payloadSpec = Object.keys(payloadOpts).map((k) => `${k}:${(payloadSel[k] ?? []).join(',')}`).join('|')
    const data = { ...form, orbits: form.orbit ? [form.orbit] : [], payloadSpec }
    await saveCluster(editTarget ? { ...editTarget, ...data } : data) // POST /clusters/saveCluster
    setEditTarget(null)
    setCreating(false)
    load()
  }

  const upload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) submitClusterFile(f).then(load) // POST /clusters/submitClusterFile
    e.target.value = ''
  }

  const ClusterForm = (
    <div className="space-y-3">
      <FormRow label="星簇名称"><input className="tech-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="星簇-XX" /></FormRow>
      <FormRow label="包含轨道">
        <select className="tech-input" value={form.orbit} onChange={(e) => { setForm({ ...form, orbit: e.target.value }); loadPayloadOptions(e.target.value) }}>
          <option value="">请选择</option>
          {orbits.map((o) => <option key={o}>{o}</option>)}
        </select>
      </FormRow>
      <FormRow label="载荷配置">
        <div className="space-y-2">
          {!form.orbit ? (
            <div className="text-xs text-[#5f83a8]">请先选择轨道</div>
          ) : Object.keys(payloadOpts).length === 0 ? (
            <div className="text-xs text-[#5f83a8]">该轨道暂无可用载荷参数</div>
          ) : (
            Object.entries(payloadOpts).map(([key, resList]) => (
              <div key={key} className="rounded border border-[rgba(0,220,255,0.15)] p-2">
                <div className="mb-1.5 text-xs text-[#9fd8ef]">{PAYLOAD_LABELS[key] ?? key}</div>
                <div className="flex flex-wrap gap-3">
                  {resList.map((r) => (
                    <span key={r} className="flex cursor-pointer items-center gap-1 text-xs text-[#d8f3ff]" onClick={() => toggleRes(key, r)}>
                      <input type="checkbox" className="pointer-events-none accent-[#00dcff]" checked={(payloadSel[key] ?? []).includes(r)} readOnly />
                      {r}m
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </FormRow>
    </div>
  )

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader
        title="星簇管理"
        sub="CLUSTER MANAGEMENT"
        right={
          <>
            <button className="tech-btn flex items-center gap-1" onClick={openCreate}><Plus size={12} />新建星簇</button>
            <label className="tech-btn-ghost flex cursor-pointer items-center gap-1">
              <Upload size={12} />导入配置<input type="file" accept=".json,.txt" className="hidden" onChange={upload} />
            </label>
            <button className="tech-btn-ghost flex items-center gap-1" onClick={() => exportAllClusters()}><Download size={12} />全部导出</button>
            <button className="tech-btn-ghost" onClick={() => setReplan({ open: true, from: list[0]?.name ?? '', to: list[1]?.name ?? '' })}>跨簇重规划</button>
            <button className="tech-btn-ghost flex items-center gap-1" onClick={load}><RefreshCw size={12} />刷新</button>
          </>
        }
      />

      {/* 星簇卡片 */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {list.map((c) => (
          <Panel key={c.id} title={c.name} sub={`CLUSTER-${c.id}`} right={<Tag text={c.available ? '运行中' : '已停用'} tone={c.available ? 'green' : 'gray'} />}>
            <div className="mb-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded bg-[rgba(0,220,255,0.06)] py-2">
                <div className="glow-text num-font text-xl font-bold">{c.satelliteCount}</div>
                <div className="text-[10px] text-[#5f83a8]">卫星数量</div>
              </div>
              <div className="rounded bg-[rgba(0,220,255,0.06)] py-2">
                <div className="glow-text num-font text-xl font-bold">{c.orbits.length}</div>
                <div className="text-[10px] text-[#5f83a8]">覆盖轨道</div>
              </div>
              <div className="rounded bg-[rgba(0,220,255,0.06)] py-2">
                <div className="glow-text text-xs font-bold leading-7">{c.payloadSpec}</div>
                <div className="text-[10px] text-[#5f83a8]">载荷配置</div>
              </div>
            </div>
            <div className="mb-3 flex flex-wrap gap-1">
              {c.orbits.map((o) => <Tag key={o} text={o} tone="cyan" />)}
            </div>
            <div className="flex items-center gap-3 border-t border-[rgba(0,220,255,0.1)] pt-2.5 text-xs">
              <a className="table-link" onClick={() => openDetail(c.name)}>详情</a>
              <a className="table-link" onClick={() => openEdit(c)}>编辑</a>
              <a className="table-link" onClick={async () => { await setAvailableCluster(c.id, !c.available); load() }}>{c.available ? '停用' : '启用'}</a>
              <a className="table-link ml-auto !text-[#ff7a7a]" onClick={async () => { await deleteClusterById(c.id); load() }}>删除</a>
            </div>
          </Panel>
        ))}
      </div>

      {/* 新建 / 编辑弹窗 */}
      <Modal
        title={creating ? '新建星簇' : '编辑星簇'}
        open={creating || !!editTarget}
        onClose={() => { setCreating(false); setEditTarget(null) }}
        footer={
          <>
            <button className="tech-btn-ghost" onClick={() => { setCreating(false); setEditTarget(null) }}>取消</button>
            <button className="tech-btn" onClick={save}>保存</button>
          </>
        }
      >
        {ClusterForm}
      </Modal>

      {/* 跨簇重规划 */}
      <Modal
        title="跨簇重规划"
        open={replan.open}
        onClose={() => setReplan({ ...replan, open: false })}
        footer={
          <>
            <button className="tech-btn-ghost" onClick={() => setReplan({ ...replan, open: false })}>取消</button>
            <button className="tech-btn" onClick={async () => { await replanCluster(replan.from, replan.to); setReplan({ ...replan, open: false }) }}>执行重规划</button>
          </>
        }
      >
        <div className="space-y-3">
          <FormRow label="源星簇">
            <select className="tech-input" value={replan.from} onChange={(e) => setReplan({ ...replan, from: e.target.value })}>
              {list.map((c) => <option key={c.id}>{c.name}</option>)}
            </select>
          </FormRow>
          <FormRow label="目标星簇">
            <select className="tech-input" value={replan.to} onChange={(e) => setReplan({ ...replan, to: e.target.value })}>
              {list.map((c) => <option key={c.id}>{c.name}</option>)}
            </select>
          </FormRow>
          <div className="rounded border border-[rgba(255,180,60,0.25)] bg-[rgba(255,180,60,0.06)] p-2 text-xs leading-5 text-[#ffb43c]">
            重规划将重新分配两个星簇内的未执行任务，执行期间相关任务短暂挂起。
          </div>
        </div>
      </Modal>

      {/* 详情弹窗 */}
      <Modal title="星簇详情" open={!!detail} onClose={() => setDetail(null)} width={620}>
        {detail && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
              {([
                ['星簇名称', detail.name], ['卫星数量', detail.satellites?.length ?? 0],
                ['包含轨道', detail.orbits?.join('、')], ['载荷配置', detail.payloadSpec],
              ] as [string, string | number][]).map(([label, v]) => (
                <div key={label} className="desc-item"><span className="label">{label}</span><span className="value">{v}</span></div>
              ))}
            </div>
            <div>
              <div className="panel-title mb-2">成员卫星</div>
              <div className="flex flex-wrap gap-1.5">
                {(detail.satellites ?? []).map((s: string) => <Tag key={s} text={s} tone="cyan" />)}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
