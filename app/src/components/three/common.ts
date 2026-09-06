import * as THREE from 'three'

/** 经纬度 → 球面坐标 */
export function ll(lat: number, lon: number, r: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta),
  )
}

/** 球面弧线（抬高 h） */
export function arc(a: THREE.Vector3, b: THREE.Vector3, h = 0.15, seg = 40): THREE.Vector3[] {
  const pts: THREE.Vector3[] = []
  for (let i = 0; i <= seg; i++) {
    const t = i / seg
    const v = new THREE.Vector3().lerpVectors(a, b, t).normalize()
    const r = a.length() + Math.sin(t * Math.PI) * h
    pts.push(v.multiplyScalar(r))
  }
  return pts
}

/** 颜色降透明度 */
export function fade(color: string, alpha: number): string {
  if (color.startsWith('#')) {
    return color + Math.round(alpha * 255).toString(16).padStart(2, '0')
  }
  const m = color.match(/rgba?\(([^)]+)\)/)
  if (!m) return color
  const parts = m[1].split(',').slice(0, 3).join(',')
  return `rgba(${parts},${alpha})`
}

/** 发光圆点 Sprite */
export function glowSprite(color: string, size: number): THREE.Sprite {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const ctx = c.getContext('2d')!
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64)
  g.addColorStop(0, color)
  g.addColorStop(0.3, fade(color, 0.55))
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, 128, 128)
  const m = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })
  const s = new THREE.Sprite(m)
  s.scale.setScalar(size)
  return s
}

/** 卫星 Sprite（本体 + 太阳翼） */
export function satelliteSprite(size: number): THREE.Sprite {
  const c = document.createElement('canvas')
  c.width = c.height = 256
  const ctx = c.getContext('2d')!
  ctx.translate(128, 128)
  ctx.lineWidth = 3
  ctx.fillStyle = '#eaf6ff'
  ctx.fillRect(-24, -30, 48, 60)
  ctx.strokeStyle = '#9fe8ff'
  ctx.strokeRect(-24, -30, 48, 60)
  ctx.fillStyle = '#1a9ae0'
  ctx.fillRect(-108, -22, 72, 44)
  ctx.fillRect(36, -22, 72, 44)
  ctx.strokeStyle = '#6ee7ff'
  ctx.strokeRect(-108, -22, 72, 44)
  ctx.strokeRect(36, -22, 72, 44)
  const m = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false })
  const s = new THREE.Sprite(m)
  s.scale.setScalar(size)
  return s
}

/** 卫星名称标签 Sprite（黄绿等宽字体 + 黑描边，对齐旧版 Cesium 风格） */
export function labelSprite(text: string): THREE.Sprite {
  const c = document.createElement('canvas')
  c.width = 256
  c.height = 56
  const ctx = c.getContext('2d')!
  ctx.font = '28px "Lucida Console", "Courier New", monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.lineWidth = 5
  ctx.strokeStyle = 'rgba(0,0,0,0.85)'
  ctx.strokeText(text, 128, 30)
  ctx.fillStyle = '#d5ff00'
  ctx.fillText(text, 128, 30)
  const m = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false })
  const s = new THREE.Sprite(m)
  s.scale.set(0.26, 0.057, 1)
  return s
}

/** 地面站 Sprite（塔架） */
export function stationSprite(size: number): THREE.Sprite {
  const c = document.createElement('canvas')
  c.width = c.height = 96
  const ctx = c.getContext('2d')!
  ctx.strokeStyle = '#d8f2ff'
  ctx.lineWidth = 4
  ctx.beginPath()
  ctx.moveTo(48, 14); ctx.lineTo(28, 80)
  ctx.moveTo(48, 14); ctx.lineTo(68, 80)
  ctx.moveTo(36, 56); ctx.lineTo(60, 56)
  ctx.stroke()
  ctx.beginPath()
  ctx.arc(48, 14, 6, 0, Math.PI * 2)
  ctx.fillStyle = '#6ee7ff'
  ctx.fill()
  const m = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false })
  const s = new THREE.Sprite(m)
  s.scale.setScalar(size)
  return s
}

/** 圆形轨道线 */
export function orbitLine(radius: number, color: number, opacity = 0.5, dash = false): THREE.Line {
  const pts: THREE.Vector3[] = []
  for (let i = 0; i <= 256; i++) {
    const a = (i / 256) * Math.PI * 2
    pts.push(new THREE.Vector3(Math.cos(a) * radius, 0, Math.sin(a) * radius))
  }
  const geo = new THREE.BufferGeometry().setFromPoints(pts)
  const mat = dash
    ? new THREE.LineDashedMaterial({ color, dashSize: 0.06, gapSize: 0.05, transparent: true, opacity })
    : new THREE.LineBasicMaterial({ color, transparent: true, opacity })
  const line = new THREE.Line(geo, mat)
  if (dash) line.computeLineDistances()
  return line
}

/**
 * 平滑卫星拖尾（基于轨道圆的等角弧线，非逐帧采样的折线）。
 * - 轨迹在数学上是完美圆弧 → 永远圆润，不会抖动/折角
 * - 头部亮、尾部渐隐（顶点色 + 顶点透明度）
 * - 每帧只写 phase uniform，不再 setFromPoints 重建几何体，性能也更好
 */
const TRAIL_SEG = 128
export const TRAIL_SPAN = Math.PI * 0.9 // 拖尾弧度

export function createSmoothTrail(radius: number, color: number) {
  // 顶点位置固定为一段圆心角 TRAIL_SPAN 的圆弧（从 -SPAN 到 0）
  const positions = new Float32Array((TRAIL_SEG + 1) * 3)
  const colors = new Float32Array((TRAIL_SEG + 1) * 3)
  const alphas = new Float32Array(TRAIL_SEG + 1)
  const c = new THREE.Color(color)
  for (let i = 0; i <= TRAIL_SEG; i++) {
    const t = i / TRAIL_SEG // 0 = 尾端, 1 = 头端(卫星当前位置)
    const a = -TRAIL_SPAN + t * TRAIL_SPAN
    positions[i * 3] = Math.cos(a) * radius
    positions[i * 3 + 1] = 0
    positions[i * 3 + 2] = Math.sin(a) * radius
    const b = Math.pow(t, 1.8) // 尾部压暗
    colors[i * 3] = c.r * b
    colors[i * 3 + 1] = c.g * b
    colors[i * 3 + 2] = c.b * b
    alphas[i] = Math.pow(t, 1.6) * 0.85
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  geo.setAttribute('alpha', new THREE.BufferAttribute(alphas, 1))
  const mat = new THREE.ShaderMaterial({
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    uniforms: { uVisible: { value: 1 } },
    vertexShader: `
      attribute float alpha;
      varying vec3 vColor;
      varying float vAlpha;
      void main() {
        vColor = color;
        vAlpha = alpha;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      varying vec3 vColor;
      varying float vAlpha;
      uniform float uVisible;
      void main() {
        gl_FragColor = vec4(vColor, vAlpha * uVisible);
      }`,
    vertexColors: true,
  })
  const line = new THREE.Line(geo, mat)
  line.frustumCulled = false
  return line
}

/** 每帧更新：把拖尾整体旋转到卫星当前角即可（angle 为卫星在轨道组内的弧度） */
export function updateSmoothTrail(trail: THREE.Line, angle: number, visible: boolean) {
  trail.rotation.y = angle
  ;(trail.material as THREE.ShaderMaterial).uniforms.uVisible.value = visible ? 1 : 0
}
