import worldJson from '@/assets/world.json'

/**
 * 用世界地图 GeoJSON 在画布上绘制地球贴图：
 * 深蓝海洋底 + 风格化大陆 + 海岸线发光 + 经纬网格。
 */
export function createEarthTexture(w = 2048, h = 1024): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')!

  const ocean = ctx.createLinearGradient(0, 0, 0, h)
  ocean.addColorStop(0, '#051a3a')
  ocean.addColorStop(0.5, '#0a2b5c')
  ocean.addColorStop(1, '#051a3a')
  ctx.fillStyle = ocean
  ctx.fillRect(0, 0, w, h)

  const px = (lon: number) => ((lon + 180) / 360) * w
  const py = (lat: number) => ((90 - lat) / 180) * h

  type Ring = number[][]
  const drawRing = (ring: Ring, fill: boolean) => {
    ctx.beginPath()
    ring.forEach(([lon, lat], i) => {
      const x = px(lon)
      const y = py(lat)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.closePath()
    if (fill) ctx.fill()
    ctx.stroke()
  }

  const features = (worldJson as any).features as any[]
  const forEachGeometry = (fn: (ring: Ring) => void) => {
    for (const f of features) {
      const g = f.geometry
      if (!g) continue
      if (g.type === 'Polygon') for (const ring of g.coordinates) fn(ring)
      else if (g.type === 'MultiPolygon') for (const poly of g.coordinates) for (const ring of poly) fn(ring)
    }
  }

  ctx.lineJoin = 'round'
  ctx.strokeStyle = 'rgba(80, 210, 255, 0.3)'
  ctx.lineWidth = 5
  forEachGeometry((ring) => drawRing(ring, false))

  ctx.fillStyle = 'rgba(32, 92, 76, 0.92)'
  ctx.strokeStyle = 'rgba(100, 225, 255, 0.75)'
  ctx.lineWidth = 1.2
  forEachGeometry((ring) => drawRing(ring, true))

  ctx.strokeStyle = 'rgba(80, 190, 255, 0.13)'
  ctx.lineWidth = 1
  for (let lon = -180; lon <= 180; lon += 20) {
    ctx.beginPath(); ctx.moveTo(px(lon), 0); ctx.lineTo(px(lon), h); ctx.stroke()
  }
  for (let lat = -80; lat <= 80; lat += 20) {
    ctx.beginPath(); ctx.moveTo(0, py(lat)); ctx.lineTo(w, py(lat)); ctx.stroke()
  }

  return canvas
}
