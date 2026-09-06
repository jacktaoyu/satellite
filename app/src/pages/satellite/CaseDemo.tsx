import { useEffect, useState } from 'react'
import { Play, Trash2 } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { PageHeader, Tag, Modal } from '@/components/ui/widgets'
import Chart, { TOOLTIP_STYLE } from '@/components/Chart'
import { getPresetCaseInfo, runCase, getCaseHistory, clearCaseHistory } from '@/api'
import type { CaseInfo } from '@/api'
import worldJson from '@/assets/world.json'
import * as echarts from 'echarts'

echarts.registerMap('world', worldJson as any)

const CASE_TYPES: { type: 'point' | 'area' | 'ocean' | 'comprehensive'; icon: string }[] = [
  { type: 'point', icon: '◇' },
  { type: 'area', icon: '▣' },
  { type: 'ocean', icon: '≋' },
  { type: 'comprehensive', icon: '✦' },
]

export default function CaseDemo() {
  const [cases, setCases] = useState<CaseInfo[]>([])
  const [selected, setSelected] = useState<CaseInfo | null>(null)
  const [running, setRunning] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])

  const loadHistory = () => getCaseHistory().then(setHistory)
  useEffect(() => {
    Promise.all(CASE_TYPES.map((c) => getPresetCaseInfo(c.type))).then((r) => { setCases(r); setSelected(r[0]) }) // GET /tasks/presetCaseInfo/{type}
    loadHistory()
  }, [])

  const run = async (type: 'point' | 'area' | 'ocean' | 'comprehensive') => {
    setRunning(type)
    const r = await runCase(type) // GET /tasks/{point|area|ocean}TargetCase | comprehensiveCase
    setRunning(null)
    setResult(r)
    loadHistory()
  }

  const mapOption = selected && {
    tooltip: { ...TOOLTIP_STYLE },
    geo: {
      map: 'world', roam: true, zoom: 1.3, center: [112, 30] as any,
      itemStyle: { areaColor: 'rgba(10,40,80,0.55)', borderColor: 'rgba(0,220,255,0.35)', borderWidth: 0.6 },
      emphasis: { disabled: true },
    },
    series: [
      selected.region.polygon.length > 0 && {
        type: 'lines', coordinateSystem: 'geo', polyline: true,
        data: [{ coords: [...selected.region.polygon.map(([lat, lon]: [number, number]) => [lon, lat]), [selected.region.polygon[0][1], selected.region.polygon[0][0]]] }],
        lineStyle: { color: '#ffc94d', width: 2, type: 'dashed' },
        effect: { show: true, period: 5, trailLength: 0.4, symbol: 'arrow', symbolSize: 5, color: '#ffc94d' },
        zlevel: 2,
      },
      selected.region.trajectory.length > 0 && {
        type: 'lines', coordinateSystem: 'geo',
        data: [{ coords: selected.region.trajectory.map(([lat, lon]: [number, number]) => [lon, lat]) }],
        lineStyle: { color: '#ff7a7a', width: 2 },
        effect: { show: true, period: 4, trailLength: 0.5, symbol: 'circle', symbolSize: 6, color: '#ff7a7a' },
        zlevel: 3,
      },
      {
        type: 'effectScatter', coordinateSystem: 'geo',
        data: [
          ...selected.region.points.map(([lat, lon]: [number, number]) => ({ value: [lon, lat] })),
          ...selected.region.trajectory.map(([lat, lon]: [number, number]) => ({ value: [lon, lat] })),
        ],
        symbolSize: 9,
        rippleEffect: { brushType: 'stroke', scale: 3 },
        itemStyle: { color: '#00dcff', shadowBlur: 8, shadowColor: '#00dcff' },
        zlevel: 4,
      },
    ].filter(Boolean),
  }

  // 综合验证案例后端不支持 presetCaseInfo 时会走 catch 返回骨架（region 全空），此时隐藏地图显示占位
  const hasRegion = !!selected && (selected.region.points.length + selected.region.polygon.length + selected.region.trajectory.length > 0)

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader title="示范用例" sub="DEMO CASES" />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        {/* 用例卡片 */}
        <div className="space-y-3">
          {cases.map((c) => (
            <Panel
              key={c.type}
              className={`cursor-pointer transition ${selected?.type === c.type ? '!border-[rgba(0,220,255,0.6)] shadow-[0_0_18px_rgba(0,220,255,0.15)]' : ''}`}
              title={`${CASE_TYPES.find((x) => x.type === c.type)?.icon} ${c.name}`}
              bodyClassName="!py-2.5"
            >
              <div onClick={() => setSelected(c)}>
              <p className="mb-2 text-xs leading-5 text-[#7ba7cc]">{c.desc}</p>
              <div className="flex items-center justify-between">
                <div className="flex gap-1">{c.tags.map((t) => <Tag key={t} text={t} tone="cyan" />)}</div>
                <button
                  className="tech-btn flex items-center gap-1"
                  disabled={running === c.type}
                  onClick={(e) => { e.stopPropagation(); run(c.type) }}
                >
                  <Play size={11} />{running === c.type ? '生成中…' : '运行'}
                </button>
              </div>
              </div>
            </Panel>
          ))}
        </div>

        {/* 详情与地图 */}
        {selected && (
          <div className="xl:col-span-2 space-y-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Panel title="任务参数" bodyClassName="grid grid-cols-2 gap-x-3 gap-y-2">
                {selected.params.map((p) => (
                  <div key={p.label} className="desc-item"><span className="label">{p.label}</span><span className="value num-font">{p.value}</span></div>
                ))}
              </Panel>
              <Panel title="验证要点" bodyClassName="!py-2.5">
                <ul className="space-y-1.5">
                  {selected.features.map((f, i) => (
                    <li key={i} className="flex gap-2 text-xs leading-5 text-[#9cc4e2]"><span className="text-[#00dcff]">▸</span>{f}</li>
                  ))}
                </ul>
                <div className="mt-3 flex items-center gap-1">
                  {selected.steps.map((s, i) => (
                    <div key={s} className="flex items-center gap-1">
                      <span className="rounded border border-[rgba(0,220,255,0.35)] bg-[rgba(0,220,255,0.08)] px-1.5 py-0.5 text-[10px] text-[#7fe8ff]">{s}</span>
                      {i < selected.steps.length - 1 && <span className="text-[#3a6d96]">→</span>}
                    </div>
                  ))}
                </div>
              </Panel>
            </div>
            <Panel title="目标区域示意" sub="TARGET REGION" bodyClassName="!p-1">
              {hasRegion
                ? <Chart height={260} option={mapOption} />
                : <div className="flex h-[260px] items-center justify-center text-xs text-[#4a6c8c]">该用例暂无目标区域坐标数据</div>}
            </Panel>
          </div>
        )}
      </div>

      {/* 运行历史 */}
      <Panel
        className="mt-3"
        title="运行历史"
        sub="HISTORY"
        right={<button className="tech-btn-ghost flex items-center gap-1" onClick={async () => { await clearCaseHistory(); loadHistory() }}><Trash2 size={11} />清空</button>}
        bodyClassName="!p-0"
      >
        <table className="tech-table">
          <thead><tr><th>用例名称</th><th>生成任务数</th><th>运行结果</th><th>运行时间</th></tr></thead>
          <tbody>
            {history.map((h, i) => (
              <tr key={i}>
                <td className="text-[#4fd8ff]">{h.name}</td>
                <td className="num-font">{h.count}</td>
                <td><Tag text={h.success ? '成功' : '失败'} tone={h.success ? 'green' : 'red'} /></td>
                <td className="num-font">{h.time}</td>
              </tr>
            ))}
            {history.length === 0 && <tr><td colSpan={4} className="py-6 text-center text-[#4a6c8c]">暂无运行记录</td></tr>}
          </tbody>
        </table>
      </Panel>

      {/* 运行结果弹窗 */}
      <Modal title="用例运行结果" open={!!result} onClose={() => setResult(null)}>
        {result && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
            {([
              ['用例名称', result.caseType], ['任务批次号', result.taskId], ['生成任务数', result.taskCount],
              ['生成时间', result.genTime], ['任务状态', result.status], ['载荷类型', result.sensorType],
              ['执行卫星', result.satellites], ['目标区域', result.target],
            ] as [string, string | number][]).map(([label, v]) => (
              <div key={label} className="desc-item"><span className="label">{label}</span><span className="value num-font">{v}</span></div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  )
}
