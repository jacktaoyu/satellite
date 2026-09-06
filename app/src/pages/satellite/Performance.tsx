import { useEffect, useState } from 'react'
import { CheckCircle2, Cpu, Download, Sigma, Timer } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { PageHeader, StatCard } from '@/components/ui/widgets'
import Chart, { AXIS_STYLE, TOOLTIP_STYLE } from '@/components/Chart'
import { getModel, getClusterData, getScheduleStatus, getAllClustersNames, exportSchedule, getCurrentTime } from '@/api'

const ALGO_COLORS: Record<string, string> = { 蚁群: '#00dcff', 遗传: '#ffc94d', 贪心: '#b18cff', 当前方案: '#4fe3a5' }
const MODE_NAMES: Record<number, string> = { 0: '综合最优方案', 1: '任务满足率最优', 2: '资源利用率最大', 3: '成像质量最高' }

export default function Performance() {
  const [tab, setTab] = useState<'algo' | 'sys'>('algo')
  const [clusters, setClusters] = useState<string[]>([])
  const [cluster, setCluster] = useState('')
  const [algoData, setAlgoData] = useState<any>(null)
  const [sysData, setSysData] = useState<any>(null)
  const [mode, setMode] = useState<number | null>(null)
  const [simTime, setSimTime] = useState('')

  useEffect(() => {
    getAllClustersNames().then((r) => { setClusters(r); setCluster(r[0] ?? '') }) // GET /clusters/getAllClustersNames
    getScheduleStatus().then(setSysData) // GET /exportScheduleStatus
    getModel().then((r) => setMode(r.mode)) // GET /getModel
    // GET /getCurrentTime —— 仿真时钟每 5 秒轮询
    const tick = () => getCurrentTime().then((t) => setSimTime(t ? t.slice(11) : ''))
    tick()
    const timer = setInterval(tick, 5000)
    return () => clearInterval(timer)
  }, [])
  useEffect(() => {
    if (cluster) getClusterData(cluster).then(setAlgoData) // GET /getClusterData/{clusterName}
  }, [cluster])

  const lineOpt = (title: string, data: number[], unit: string, color = '#00dcff') => ({
    title: { text: title, textStyle: { color: '#7fe8ff', fontSize: 12, fontWeight: 500 }, left: 8, top: 4 },
    grid: { left: 48, right: 16, top: 36, bottom: 24 },
    tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
    xAxis: { type: 'category', data: algoData?.time ?? [], ...AXIS_STYLE },
    yAxis: { type: 'value', name: unit, ...AXIS_STYLE },
    series: [{
      type: 'line', data, smooth: true, symbol: 'none',
      lineStyle: { color, width: 1.8 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: color + '44' }, { offset: 1, color: 'rgba(0,0,0,0)' }] } },
    }],
  })

  const compareOpt = (title: string, seriesMap: Record<string, number[]>, unit: string) => ({
    title: { text: title, textStyle: { color: '#7fe8ff', fontSize: 12, fontWeight: 500 }, left: 8, top: 4 },
    grid: { left: 48, right: 16, top: 44, bottom: 24 },
    tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
    legend: { top: 4, right: 8, textStyle: { color: '#7ba7cc', fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
    xAxis: { type: 'category', data: sysData?.time ?? [], ...AXIS_STYLE },
    yAxis: { type: 'value', name: unit, ...AXIS_STYLE },
    series: Object.entries(seriesMap ?? {}).map(([name, data]) => ({
      name, type: 'line', data, smooth: true, symbol: 'none',
      lineStyle: { color: ALGO_COLORS[name] ?? '#00dcff', width: name === '当前方案' ? 2.4 : 1.2, type: name === '当前方案' ? 'solid' : 'dashed' },
    })),
  })

  const radarOpt = sysData && {
    tooltip: TOOLTIP_STYLE,
    legend: { bottom: 0, textStyle: { color: '#7ba7cc', fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
    radar: {
      indicator: sysData.radar.indicators.map((n: string) => ({ name: n, max: 100 })),
      radius: '62%', center: ['50%', '48%'],
      axisName: { color: '#7ba7cc', fontSize: 10 },
      splitArea: { areaStyle: { color: ['rgba(0,220,255,0.03)', 'rgba(0,220,255,0.06)'] } },
      splitLine: { lineStyle: { color: 'rgba(0,220,255,0.15)' } },
      axisLine: { lineStyle: { color: 'rgba(0,220,255,0.2)' } },
    },
    series: [{
      type: 'radar',
      data: ['贪心', '蚁群', '遗传'].map((k) => ({
        name: k, value: sysData.radar[k],
        lineStyle: { color: ALGO_COLORS[k] }, itemStyle: { color: ALGO_COLORS[k] },
        areaStyle: { color: ALGO_COLORS[k] + '22' },
      })),
    }],
  }

  const execOpt = sysData && {
    grid: { left: 48, right: 16, top: 36, bottom: 24 },
    tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
    legend: { top: 4, right: 8, textStyle: { color: '#7ba7cc', fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
    xAxis: { type: 'category', data: sysData.execution.labels, ...AXIS_STYLE },
    yAxis: { type: 'value', ...AXIS_STYLE },
    series: [
      { name: '执行成功', type: 'bar', stack: 't', data: sysData.execution.success, barWidth: 22, itemStyle: { color: '#00dcff', borderRadius: [0, 0, 0, 0] } },
      { name: '执行失败', type: 'bar', stack: 't', data: sysData.execution.fail, barWidth: 22, itemStyle: { color: '#ff7a7a', borderRadius: [3, 3, 0, 0] } },
    ],
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader title="性能分析" sub="PERFORMANCE ANALYSIS" />

      {/* Tabs */}
      <div className="mb-3 flex gap-1 rounded border border-[rgba(0,220,255,0.25)] p-0.5 self-start w-fit">
        {([['algo', '算法性能'], ['sys', '系统性能']] as const).map(([k, label]) => (
          <button key={k} className={`rounded px-5 py-1.5 text-xs transition ${tab === k ? 'bg-[rgba(0,220,255,0.18)] text-[#4fd8ff]' : 'text-[#6b93b8] hover:text-[#a8cbe8]'}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'algo' && (
        <>
          <Panel className="mb-3 shrink-0" bodyClassName="flex items-center gap-8 !py-2.5">
            <span className="text-xs text-[#7ba7cc]">
              当前系统模式：<span className="text-[#4fd8ff]">{mode != null ? (MODE_NAMES[mode] ?? '未知模式') : '—'}</span>
            </span>
            <span className="text-xs text-[#7ba7cc]">
              当前系统时间：<span className="num-font text-[#d8f2ff]">{simTime || '--:--:--'}</span>
            </span>
          </Panel>
          <Panel className="mb-3 shrink-0" bodyClassName="flex items-center gap-3 !py-2.5">
            <span className="text-xs text-[#7ba7cc]">选择星簇</span>
            <select className="tech-input w-44" value={cluster} onChange={(e) => setCluster(e.target.value)}>
              {clusters.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Panel>
          {algoData && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Panel bodyClassName="!p-1"><Chart height={220} option={lineOpt('任务数量变化', algoData.taskCount, '个')} /></Panel>
              <Panel bodyClassName="!p-1"><Chart height={220} option={lineOpt('星簇总功耗', algoData.power, 'W', '#ffc94d')} /></Panel>
              <Panel bodyClassName="!p-1"><Chart height={220} option={lineOpt('存储占用量', algoData.storage, 'GB', '#b18cff')} /></Panel>
              <Panel bodyClassName="!p-1"><Chart height={220} option={lineOpt('存储利用率', algoData.storageRate, '%', '#4fe3a5')} /></Panel>
            </div>
          )}
        </>
      )}

      {tab === 'sys' && sysData && (
        <>
          <div className="mb-3 grid grid-cols-2 gap-3 xl:grid-cols-4">
            <StatCard label="任务完成率" value={sysData.stats.completeRate} unit="%" tone="cyan" icon={CheckCircle2} />
            <StatCard label="资源利用率" value={sysData.stats.resourceRate} unit="%" tone="green" icon={Cpu} />
            <StatCard label="平均规划耗时" value={sysData.stats.avgPlanTime} unit="s" tone="amber" icon={Timer} />
            <StatCard label="累计规划轮次" value={sysData.stats.planCount} unit="次" tone="violet" icon={Sigma} />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Panel bodyClassName="!p-1"><Chart height={220} option={compareOpt('任务完成率对比', sysData.compare.completeRate, '%')} /></Panel>
            <Panel bodyClassName="!p-1"><Chart height={220} option={compareOpt('规划耗时对比', sysData.compare.planTime, 's')} /></Panel>
            <Panel bodyClassName="!p-1"><Chart height={220} option={compareOpt('功耗对比', sysData.compare.power, 'W')} /></Panel>
            <Panel bodyClassName="!p-1"><Chart height={220} option={compareOpt('存储占用对比', sysData.compare.storage, 'GB')} /></Panel>
            <Panel title="算法综合雷达" bodyClassName="!p-1"><Chart height={260} option={radarOpt} /></Panel>
            <Panel title="各类型任务执行情况" bodyClassName="!p-1"><Chart height={260} option={execOpt} /></Panel>
          </div>

          {/* 明细表 */}
          <Panel
            className="mt-3"
            title="算法评测明细"
            sub="EVALUATION DETAIL"
            right={
              <div className="flex gap-2">
                {(['greedy', 'ant', 'genetic', 'schedule'] as const).map((t, i) => (
                  <button key={t} className="tech-btn-ghost flex items-center gap-1" onClick={() => exportSchedule(t)}>
                    <Download size={11} />{['贪心', '蚁群', '遗传', '当前方案'][i]}
                  </button>
                ))}
              </div>
            }
            bodyClassName="!p-0"
          >
            <table className="tech-table">
              <thead>
                <tr><th>算法</th><th>完成率 %</th><th>资源利用率 %</th><th>成像质量</th><th>总功耗 W</th><th>总存储 GB</th><th>规划耗时 s</th><th>评测时间</th></tr>
              </thead>
              <tbody>
                {sysData.table.map((r: any) => (
                  <tr key={r.algo} className={r.algo === '当前方案' ? '!bg-[rgba(79,227,165,0.06)]' : ''}>
                    <td className={r.algo === '当前方案' ? 'text-[#4fe3a5]' : 'text-[#4fd8ff]'}>{r.algo}</td>
                    <td className="num-font">{r.complete}</td>
                    <td className="num-font">{r.resource}</td>
                    <td className="num-font">{r.quality}</td>
                    <td className="num-font">{r.power}</td>
                    <td className="num-font">{r.storage}</td>
                    <td className="num-font">{r.planTime}</td>
                    <td className="num-font">{r.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </>
      )}
    </div>
  )
}
