import { useEffect, useState } from 'react'
import Panel from '@/components/ui/Panel'
import { PageHeader, FormRow, Tag, sensorTone } from '@/components/ui/widgets'
import { getNetworkParameters, saveNetworkParameters } from '@/api'
import type { SensorType, PayloadParams } from '@/api'

// 说明书 3.7.6 卫星参数模块：九项载荷参数
const PARAM_FIELDS: [keyof PayloadParams, string][] = [
  ['storage', '存储容量 GB'],
  ['battery', '电池容量 Wh'],
  ['resolution', '分辨率 m'],
  ['width', '幅宽最大值 km'],
  ['sideAngle', '最大侧摆角 °'],
  ['pitchAngle', '最大俯仰角 °'],
  ['angularVelocity', '载荷转动角速度 rad/s'],
  ['settlingTime', '稳定时间 s'],
  ['threshold', '云层遮挡厚度阈值 m'],
]

const DEFAULT_VALUE: PayloadParams = {
  storage: 500, battery: 5000, resolution: 0.5, width: 50, sideAngle: 45,
  pitchAngle: 45, angularVelocity: 5, settlingTime: 10, threshold: 800,
}

const DEFAULTS: Record<SensorType, PayloadParams> = {
  光学: { ...DEFAULT_VALUE },
  SAR: { ...DEFAULT_VALUE },
  红外: { ...DEFAULT_VALUE },
}

export default function NetworkParameters() {
  const [params, setParams] = useState<Record<SensorType, PayloadParams>>(DEFAULTS)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    // GET /networkParameters —— 返回非 null 则用真实配置填充，null 保留内置默认值
    getNetworkParameters().then((r) => {
      if (!r) return
      setParams((p) => {
        const next = { ...p }
        for (const type of Object.keys(next) as SensorType[]) {
          const v = r[type]
          if (!v || typeof v !== 'object') continue
          const merged = { ...next[type] }
          for (const [field] of PARAM_FIELDS) {
            const val = v[field]
            if (typeof val === 'number') merged[field] = val
          }
          next[type] = merged
        }
        return next
      })
    })
  }, [])

  const update = (type: SensorType, key: keyof PayloadParams, v: string) =>
    setParams((p) => ({ ...p, [type]: { ...p[type], [key]: +v } }))

  const saveAll = async () => {
    // POST /networkParameters —— 三类载荷九项参数全量提交
    const r = await saveNetworkParameters(params)
    if (r && r.code !== 200 && r.code !== 0) return
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader
        title="载荷网络参数"
        sub="PAYLOAD NETWORK PARAMETERS"
        right={
          <div className="flex items-center gap-2">
            {saved && <span className="text-xs text-[#4fe3a5]">✓ 已保存并下发</span>}
            <button className="tech-btn" onClick={saveAll}>保存并下发全部</button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        {(Object.keys(params) as SensorType[]).map((type) => (
          <Panel key={type} title={`${type}载荷`} sub={type === '光学' ? 'OPTICAL' : type} right={<Tag text={type} tone={sensorTone(type)} />}>
            <div className="grid grid-cols-2 gap-3">
              {PARAM_FIELDS.map(([key, label]) => (
                <FormRow key={key} label={label}>
                  <input
                    className="tech-input"
                    type="number"
                    value={params[type][key] ?? 0}
                    onChange={(e) => update(type, key, e.target.value)}
                  />
                </FormRow>
              ))}
            </div>
            <div className="mt-3 border-t border-[rgba(0,220,255,0.1)] pt-2 text-[10px] leading-4 text-[#4a6c8c]">
              参数将下发至所有「{type}」载荷卫星并即时生效
            </div>
          </Panel>
        ))}
      </div>
    </div>
  )
}
