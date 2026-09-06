import { useEffect, useState } from 'react'
import Panel from '@/components/ui/Panel'
import { PageHeader, Tag, Pagination } from '@/components/ui/widgets'
import Chart, { TOOLTIP_STYLE } from '@/components/Chart'
import { getGroundStationInfo } from '@/api'
import type { GroundStation as GS } from '@/api'
import worldJson from '@/assets/world.json'
import * as echarts from 'echarts'

echarts.registerMap('world', worldJson as any)

export default function GroundStation() {
  const [stations, setStations] = useState<GS[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(5)

  useEffect(() => {
    // GET /satellites/groundStationInfo —— 每 5 秒轮询，保持关联卫星列表实时同步
    const load = () => getGroundStationInfo().then(setStations)
    load()
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [])

  const pageData = stations.slice((page - 1) * pageSize, page * pageSize)

  const mapOption = {
    tooltip: { ...TOOLTIP_STYLE, formatter: (p: any) => p.data ? `<b>${p.name}</b><br/>连接卫星 ${p.data.value} 颗` : p.name },
    geo: {
      map: 'world',
      roam: true,
      zoom: 1.15,
      center: [105, 34] as any,
      itemStyle: { areaColor: 'rgba(10,40,80,0.55)', borderColor: 'rgba(0,220,255,0.35)', borderWidth: 0.6 },
      emphasis: { itemStyle: { areaColor: 'rgba(0,120,180,0.5)' }, label: { show: false } },
      label: { show: false },
    },
    series: [{
      type: 'effectScatter',
      coordinateSystem: 'geo',
      data: stations.map((s) => ({ name: s.name, value: [s.location[1], s.location[0], s.connecting_satellite.length] })),
      symbolSize: 12,
      rippleEffect: { brushType: 'stroke', scale: 3.5 },
      itemStyle: { color: '#00dcff', shadowBlur: 10, shadowColor: '#00dcff' },
      label: { show: true, position: 'top', formatter: '{b}', color: '#7fe8ff', fontSize: 11, textShadowColor: '#02101f', textShadowBlur: 4 },
      zlevel: 2,
    }],
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <PageHeader title="地面站管理" sub="GROUND STATION" />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-5">
        <Panel className="xl:col-span-3" title="地面站全球分布" sub="STATION MAP" bodyClassName="!p-1">
          <Chart height={430} option={mapOption} />
        </Panel>
        <div className="xl:col-span-2 space-y-3">
          {pageData.map((s) => (
            <Panel key={s.name} title={s.name} bodyClassName="!py-2.5">
              <div className="mb-2 flex gap-6 text-xs text-[#7ba7cc]">
                <span>纬度 <span className="num-font text-[#c2e4ff]">{s.location[0].toFixed(2)}°</span></span>
                <span>经度 <span className="num-font text-[#c2e4ff]">{s.location[1].toFixed(2)}°</span></span>
                <span>在线卫星 <span className="num-font text-[#4fe3a5]">{s.connecting_satellite.length}</span></span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {s.connecting_satellite.length > 0
                  ? s.connecting_satellite.map((sat) => <Tag key={sat} text={sat} tone="green" />)
                  : <span className="text-xs text-[#4a6c8c]">当前无连接卫星</span>}
              </div>
            </Panel>
          ))}
          <Pagination
            page={page}
            total={stations.length}
            pageSize={pageSize}
            onChange={setPage}
            onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
            pageSizeOptions={[3, 5, 10]}
          />
        </div>
      </div>
    </div>
  )
}
