import { useEffect, useRef, useState } from 'react'
import Panel from '@/components/ui/Panel'
import Chart, { AXIS_STYLE, TOOLTIP_STYLE } from '@/components/Chart'
import SatelliteNetworkScene from '@/components/three/SatelliteNetworkScene'
import type { NetworkSceneHandles, SceneSatellite } from '@/components/three/SatelliteNetworkScene'
import { Progress, Switch, Tag, sensorTone } from '@/components/ui/widgets'
import { getCurrentTime, getAllSatellites, getTasksByCondition, getPlanningEvaluation, getEvents, getGroundStationInfo } from '@/api'
import type { Satellite, Task, Event, GroundStation } from '@/api'

export default function SatelliteNetwork() {
  const [sats, setSats] = useState<Satellite[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [stations, setStations] = useState<GroundStation[]>([])
  const [simTime, setSimTime] = useState('')
  const [selected, setSelected] = useState<Satellite | null>(null)
  const [evalData, setEvalData] = useState<Awaited<ReturnType<typeof getPlanningEvaluation>>>()
  const [switches, setSwitches] = useState({ trails: true, cones: false, events: true, links: true })
  const [hiddenIds, setHiddenIds] = useState<Set<number>>(new Set())
  const sceneRef = useRef<NetworkSceneHandles>(null)

  // 每 5 秒整体刷新
  useEffect(() => {
    let alive = true
    const refresh = async () => {
      const [s, t, e, ev, tm] = await Promise.all([
        getAllSatellites(),        // POST /satellites/getAllSatellites
        getTasksByCondition(),     // GET /tasks/getNewTasksByCondition
        getPlanningEvaluation(),   // GET /getPlanningEvaluation
        getEvents(),
        getCurrentTime(),          // GET /getCurrentTime
      ])
      if (!alive) return
      setSats(s)
      setTasks(t)
      setEvalData(e)
      setSimTime(tm)
      setEvents((prev) => [...ev, ...prev].slice(0, 30))
      setSelected((prev) => (prev ? s.find((x) => x.id === prev.id) ?? prev : prev))
    }
    refresh()
    const timer = setInterval(refresh, 5000)
    return () => { alive = false; clearInterval(timer) }
  }, [])

  // 地面站只需拉取一次（静态配置）
  useEffect(() => {
    getGroundStationInfo().then(setStations) // GET /satellites/groundStationInfo
  }, [])

  const sceneSats: SceneSatellite[] = sats.map((s) => ({
    id: s.id, name: s.name, orbit: s.orbit, sensorType: s.sensorType,
    battery: s.battery, visible: !hiddenIds.has(s.id),
    tle1: s.tle1, tle2: s.tle2,
    linkedStations: s.linkedStations, linkedGeo: s.linkedGeo,
  }))

  const runningTasks = tasks.filter((t) => t.status === '执行中')
  const pieData = ['光学', 'SAR', '红外'].map((type) => ({
    name: type,
    value: sats.filter((s) => s.sensorType === type).length,
  }))

  const focus = (id: number) => {
    setSelected(sats.find((s) => s.id === id) ?? null)
    sceneRef.current?.flyTo(id)
  }

  return (
    <div className="relative h-full overflow-hidden">
      {/* 3D 全屏场景 */}
      <div className="absolute inset-0">
        <SatelliteNetworkScene
          ref={sceneRef}
          satellites={sceneSats}
          stations={stations.map((s) => ({ name: s.name, lat: s.location[0], lon: s.location[1] }))}
          showTrails={switches.trails}
          showCones={switches.cones}
          showLinks={switches.links}
          simTime={simTime}
          selectedId={selected?.id ?? null}
          onSelect={focus}
        />
      </div>

      {/* 顶部标题栏 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-start justify-between px-4 pt-2">
        <div className="pointer-events-auto flex gap-2">
          {[
            { label: '在线卫星', value: sats.filter((s) => s.available).length, unit: '颗', color: '#4ff3ff' },
            { label: '正在执行任务', value: runningTasks.length, unit: '个', color: '#4fe3a5' },
            { label: '任务满足率', value: evalData?.satisfactionRate ?? '-', unit: '%', color: '#ffc94d' },
            { label: '规划耗时', value: evalData?.planningTime ?? '-', unit: 's', color: '#b89dff' },
          ].map((m) => (
            <div key={m.label} className="tech-panel px-3 py-1.5 text-center">
              <div className="text-[9px] text-[#5d8cb8]">{m.label}</div>
              <div className="num-font text-lg font-bold leading-tight" style={{ color: m.color, textShadow: `0 0 10px ${m.color}66` }}>
                {m.value}<span className="ml-0.5 text-[9px] font-normal text-[#7ea6d8]">{m.unit}</span>
              </div>
            </div>
          ))}
        </div>
        <h1 className="flex items-center gap-4 rounded px-8 py-1.5 text-xl font-bold tracking-[0.3em] text-[#e0f6ff]" style={{ textShadow: '0 0 20px rgba(0,220,255,0.7)', background: 'linear-gradient(90deg, transparent, rgba(2,12,27,0.82) 18%, rgba(2,12,27,0.82) 82%, transparent)' }}>
          <i className="title-wing" />
          智能星簇协同运行验证系统 - 卫星网络态势监控
          <i className="title-wing right" />
        </h1>
        <div className="pointer-events-auto tech-panel px-3 py-1.5 text-right">
          <div className="text-[9px] text-[#5d8cb8]">仿真时间</div>
          <div className="num-font text-base font-bold text-[#4ff3ff]">{simTime.slice(11) || '--:--:--'}</div>
        </div>
      </div>

      {/* 左侧面板 */}
      <div className="absolute bottom-10 left-3 top-[64px] z-10 flex w-[230px] flex-col gap-2">
        <Panel title="实时卫星列表" sub={`${sats.length}`} className="min-h-0 flex-[3]" bodyClassName="overflow-y-auto !px-1.5">
          {sats.map((s) => (
            <div key={s.id} className="table-row-hover flex cursor-pointer items-center gap-1.5 border-b border-[rgba(0,200,255,0.08)] px-1.5 py-1.5" onClick={() => focus(s.id)}>
              <input
                type="checkbox"
                checked={!hiddenIds.has(s.id)}
                onClick={(e) => e.stopPropagation()}
                onChange={() => setHiddenIds((prev) => {
                  const next = new Set(prev)
                  next.has(s.id) ? next.delete(s.id) : next.add(s.id)
                  return next
                })}
                className="accent-[#00dcff]"
              />
              <span className="min-w-0 flex-1 truncate text-[11px] text-[#b8d8f0]">{s.name}</span>
              <Tag text={s.sensorType} tone={sensorTone(s.sensorType)} />
              <span className={`num-font text-[10px] ${s.battery < 20 ? 'text-[#ff7a7a]' : 'text-[#7ea6d8]'}`}>{s.battery}Wh</span>
            </div>
          ))}
        </Panel>

        <Panel title="任务执行进度" sub={`${runningTasks.length}`} className="min-h-0 flex-[2]" bodyClassName="overflow-y-auto">
          {runningTasks.slice(0, 6).map((t) => (
            <div key={t.id} className="mb-2">
              <div className="mb-0.5 flex justify-between text-[10px]">
                <span className="truncate text-[#b8d8f0]">{t.name}</span>
                <span className="num-font text-[#7ea6d8]">{t.progress != null ? `${t.progress}%` : '—'}</span>
              </div>
              {t.progress != null && <Progress value={t.progress} color={t.emergency ? '#ffc94d' : '#00dcff'} />}
            </div>
          ))}
        </Panel>

        <Panel title="载荷类型分布" className="h-[120px] shrink-0" bodyClassName="flex items-center">
          <div className="h-full flex-1">
            <Chart
              option={{
                tooltip: { ...TOOLTIP_STYLE },
                series: [{
                  type: 'pie', radius: ['52%', '75%'], label: { show: false },
                  data: pieData.map((d, i) => ({ ...d, itemStyle: { color: ['#00dcff', '#ffc94d', '#4fe3a5'][i] } })),
                }],
              }}
            />
          </div>
          <div className="w-[72px] space-y-1 text-[10px] text-[#8fb8e8]">
            {pieData.map((d, i) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <i className="dot" style={{ background: ['#00dcff', '#ffc94d', '#4fe3a5'][i] }} />{d.name} {d.value}
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="常用功能" className="shrink-0">
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] text-[#8fb8e8]">
            {([['trails', '全部轨迹'], ['cones', '全部视锥体'], ['events', '实时事件栏'], ['links', '通信链路']] as const).map(([k, label]) => (
              <label key={k} className="flex cursor-pointer items-center justify-between">
                {label}
                <Switch size="sm" checked={switches[k]} onChange={(v) => setSwitches({ ...switches, [k]: v })} />
              </label>
            ))}
          </div>
        </Panel>
      </div>

      {/* 右侧面板 */}
      <div className="absolute bottom-10 right-3 top-[64px] z-10 flex w-[230px] flex-col gap-2">
        {selected ? (
          <Panel
            title="卫星详情"
            className="shrink-0"
            right={<button className="tech-btn-ghost !px-2 !py-0.5 !text-[10px]" onClick={() => setSelected(null)}>隐藏</button>}
          >
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-[13px] font-bold text-[#4ff3ff]">{selected.name}</span>
              <Tag text={selected.sensorType} tone={sensorTone(selected.sensorType)} />
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[10px]">
              {[
                ['纬度', `${selected.lat.toFixed(2)}°`], ['经度', `${selected.lon.toFixed(2)}°`],
                ['高度', `${selected.altitude} km`], ['分辨率', `${selected.resolution} m`],
                ['电量', `${selected.battery} Wh`], ['存储', `${selected.storage} GB`],
                ['周期', `${selected.period} min`], ['俯仰角', `${selected.pitch}°`],
                ['侧摆角', `${selected.roll}°`],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-[rgba(0,200,255,0.08)] py-0.5">
                  <span className="text-[#5d8cb8]">{k}</span>
                  <span className="num-font text-[#d8f2ff]">{v}</span>
                </div>
              ))}
              <div className="col-span-2 flex justify-between border-b border-[rgba(0,200,255,0.08)] py-0.5">
                <span className="text-[#5d8cb8]">相连地面站</span>
                <span className="text-[#d8f2ff]">{selected.linkedStations.join('、') || '无'}</span>
              </div>
              <div className="col-span-2 flex justify-between py-0.5">
                <span className="text-[#5d8cb8]">相连高轨卫星</span>
                <span className="text-[#d8f2ff]">{selected.linkedGeo}</span>
              </div>
            </div>
            <div className="mt-1.5 flex gap-3 text-[10px] text-[#8fb8e8]">
              <label className="flex items-center gap-1.5">显示路径<Switch size="sm" checked={switches.trails} onChange={(v) => setSwitches({ ...switches, trails: v })} /></label>
              <label className="flex items-center gap-1.5">视锥体<Switch size="sm" checked={switches.cones} onChange={(v) => setSwitches({ ...switches, cones: v })} /></label>
            </div>
          </Panel>
        ) : (
          <Panel title="卫星详情" className="shrink-0">
            <div className="py-6 text-center text-[11px] text-[#3d6491]">点击左侧列表或 3D 场景中的卫星查看详情</div>
          </Panel>
        )}

        <Panel title="任务状态统计" className="h-[130px] shrink-0">
          <Chart
            option={{
              grid: { left: 28, right: 8, top: 12, bottom: 20 },
              tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
              xAxis: { type: 'category', data: ['等待规划', '正在执行', '已完成'], ...AXIS_STYLE },
              yAxis: { type: 'value', ...AXIS_STYLE },
              series: [{
                type: 'bar', barWidth: 18,
                data: [
                  { value: evalData?.taskStats.waiting ?? 0, itemStyle: { color: '#ffc94d' } },
                  { value: evalData?.taskStats.running ?? 0, itemStyle: { color: '#00dcff' } },
                  { value: evalData?.taskStats.done ?? 0, itemStyle: { color: '#4fe3a5' } },
                ],
              }],
            }}
          />
        </Panel>

        <Panel title="任务满足率趋势" className="min-h-0 flex-1" sub="最近10次规划">
          <Chart
            option={{
              grid: { left: 28, right: 8, top: 12, bottom: 20 },
              tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
              xAxis: { type: 'category', data: evalData?.trend.map((p) => `${p.round}`) ?? [], ...AXIS_STYLE },
              yAxis: { type: 'value', min: 60, max: 100, ...AXIS_STYLE },
              series: [{
                type: 'line', smooth: true, symbol: 'circle', symbolSize: 3,
                data: evalData?.trend.map((p) => p.rate) ?? [],
                lineStyle: { color: '#00dcff', width: 1.5 },
                itemStyle: { color: '#00dcff' },
                areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
                  { offset: 0, color: 'rgba(0,220,255,0.3)' }, { offset: 1, color: 'rgba(0,220,255,0.02)' },
                ] } },
              }],
            }}
          />
        </Panel>
      </div>

      {/* 底部实时事件滚动栏 */}
      {switches.events && (
        <div className="absolute inset-x-0 bottom-0 z-10 flex h-9 items-center border-t border-[rgba(0,200,255,0.2)] bg-[rgba(3,12,32,0.85)] backdrop-blur-sm">
          <span className="shrink-0 border-r border-[rgba(0,200,255,0.2)] px-3 text-[11px] font-bold text-[#4fd8ff]">实时事件</span>
          <div className="relative min-w-0 flex-1 overflow-hidden">
            <div className="flex w-max gap-10 whitespace-nowrap px-4 text-[11px]" style={{ animation: 'marquee 40s linear infinite' }}>
              {[...events, ...events].map((e, i) => (
                <span key={`${e.id}-${i}`} className="flex items-center gap-1.5">
                  <i className="dot" style={{ background: e.level === 'alarm' ? '#ff5252' : e.level === 'warning' ? '#ffc94d' : '#00dcff' }} />
                  <span className="num-font text-[#5d8cb8]">{e.time}</span>
                  <span className={e.level === 'alarm' ? 'text-[#ff8d8d]' : e.level === 'warning' ? 'text-[#ffc94d]' : 'text-[#8fb8e8]'}>{e.content}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
