import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { ArrowLeft, Download } from 'lucide-react'
import Panel from '@/components/ui/Panel'
import { Tag, sensorTone } from '@/components/ui/widgets'
import { getSatelliteByName, exportSatelliteInfo } from '@/api'
import type { Satellite } from '@/api'

const GROUPS: { title: string; items: [string, (s: Satellite) => string | number][] }[] = [
  {
    title: '基础信息',
    items: [
      ['卫星编号', (s) => s.id], ['卫星名称', (s) => s.name], ['所属轨道', (s) => s.orbit],
      ['载荷类型', (s) => s.sensorType], ['当前状态', (s) => (s.available ? '可用' : '不可用')], ['累计圈数', (s) => s.laps],
    ],
  },
  {
    title: '轨道参数（TLE 解算）',
    items: [
      ['经度', (s) => `${s.lon.toFixed(3)}°`], ['纬度', (s) => `${s.lat.toFixed(3)}°`], ['轨道高度', (s) => `${s.altitude} km`],
      ['轨道周期', (s) => `${s.period} min`], ['当前俯仰角', (s) => `${s.pitch}°`], ['当前侧摆角', (s) => `${s.roll}°`],
    ],
  },
  {
    title: '资源与功率',
    items: [
      ['剩余电量', (s) => `${s.battery} Wh`], ['剩余存储', (s) => `${s.storage} GB`], ['下行速率', (s) => `${s.downlinkRate} GB/s`],
      ['空闲功率', (s) => `${s.power.idle} W`], ['太阳能功率', (s) => `${s.power.solar} W`], ['成像功率', (s) => `${s.power.imaging} W`],
    ],
  },
  {
    title: '载荷能力',
    items: [
      ['地面分辨率', (s) => `${s.resolution} m`], ['幅宽', (s) => `${s.payload.swath} km`], ['最大侧摆角', (s) => `±${s.payload.maxRoll}°`],
      ['最大俯仰角', (s) => `±${s.payload.maxPitch}°`], ['转动速度', (s) => `${s.payload.rotateSpeed} °/s`], ['稳定时间', (s) => `${s.payload.stableTime} s`],
    ],
  },
]

export default function SatelliteDetail() {
  const { name } = useParams()
  const navigate = useNavigate()
  const [sat, setSat] = useState<Satellite | null>(null)

  useEffect(() => {
    if (name) getSatelliteByName(decodeURIComponent(name)).then((r) => setSat(r ?? null)) // POST /satellites/getSatelliteByName
  }, [name])

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="mb-3 flex items-center gap-3">
        <button className="tech-btn-ghost flex items-center gap-1" onClick={() => navigate(-1)}><ArrowLeft size={13} />返回</button>
        {sat && <button className="tech-btn-ghost flex items-center gap-1" onClick={() => exportSatelliteInfo(sat.id)}><Download size={13} />导出 Excel</button>}
        <div>
          <div className="text-base font-semibold tracking-wide text-[#d8f3ff]">卫星详情 — <span className="text-[#00dcff]">{sat?.name}</span></div>
          <div className="text-[10px] tracking-[0.3em] text-[#3a6d96]">SATELLITE DETAIL</div>
        </div>
        {sat && <div className="ml-3"><Tag text={sat.sensorType} tone={sensorTone(sat.sensorType)} /></div>}
      </div>

      {sat && (
        <>
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {GROUPS.map((g) => (
              <Panel key={g.title} title={g.title} bodyClassName="grid grid-cols-2 gap-x-4 gap-y-2.5">
                {g.items.map(([label, fn]) => (
                  <div key={label} className="desc-item">
                    <span className="label">{label}</span>
                    <span className="value num-font">{fn(sat)}</span>
                  </div>
                ))}
              </Panel>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
