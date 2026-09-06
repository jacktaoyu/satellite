import ReactECharts from 'echarts-for-react'

export const AXIS_STYLE = {
  axisLine: { lineStyle: { color: 'rgba(0,180,255,0.3)' } },
  axisLabel: { color: '#5d8cb8', fontSize: 9 },
  splitLine: { lineStyle: { color: 'rgba(0,140,240,0.1)' } },
  axisTick: { show: false },
} as const

export const TOOLTIP_STYLE = {
  backgroundColor: 'rgba(4,18,44,0.94)',
  borderColor: 'rgba(0,200,255,0.5)',
  textStyle: { color: '#d8f2ff', fontSize: 11 },
} as const

export default function Chart({ option, className, height }: { option: any; className?: string; height?: number }) {
  return (
    <ReactECharts
      option={option}
      className={className}
      style={{ height: height ?? '100%', width: '100%' }}
      notMerge
      opts={{ renderer: 'canvas' }}
    />
  )
}
