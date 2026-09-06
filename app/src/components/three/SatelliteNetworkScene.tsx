import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import * as THREE from 'three'
import * as sat from 'satellite.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import earthUrl from '@/assets/earth.jpg'
import { ll, glowSprite, satelliteSprite, stationSprite, orbitLine, labelSprite } from './common'

export interface SceneSatellite {
  id: number
  name: string
  orbit: string
  sensorType: string
  battery: number
  visible: boolean
  /** TLE 两行根数（后端 getAllSatelliteInfo 提供） */
  tle1?: string
  tle2?: string
  /** 真实连接的地面站名称列表（connecting_ground_station） */
  linkedStations: string[]
  /** 真实连接的高轨卫星名称（connecting_geo），如「高轨卫星2」 */
  linkedGeo: string
}

export interface SceneStation {
  name: string
  lat: number
  lon: number
}

export interface NetworkSceneHandles {
  /** 聚焦某颗卫星（相机飞向它） */
  flyTo: (id: number) => void
}

const GEO_SATS = [
  { name: '高轨卫星1', lon: 120 },
  { name: '高轨卫星2', lon: -120 }, // 东经 240°
  { name: '高轨卫星3', lon: 0 },
]

const SENSOR_COLOR: Record<string, number> = { 光学: 0x00dcff, SAR: 0x4fe3a5, 红外: 0xffc94d }

const EARTH_R_KM = 6371
/** 视锥体最大长度 1000km（对齐旧版 Cesium FrustumGeometry） */
const CONE_MAX_LEN = 1000 / EARTH_R_KM
/** 拖尾轨迹：过去 35 分钟，每 70 秒采样一个点 */
const TRAIL_POINTS = 30
const TRAIL_STEP_MS = 70 * 1000
/** 每帧重算拖尾的卫星数量（轮转分摊开销） */
const TRAILS_PER_FRAME = 6
/** 相机距地心小于该值时显示卫星文字标签 */
const LABEL_DIST = 3.2

interface SatNode {
  id: number
  name: string
  sensorType: string
  sprite: THREE.Sprite
  glow: THREE.Sprite
  cone: THREE.Mesh
  trail: THREE.Line
  label: THREE.Sprite
  satrec: sat.SatRec
}

/** 解析后端仿真时间字符串（后端按 UTC 解释，见 SatelliteService.ts.utc(...)） */
function parseSimTime(s: string): number {
  let iso = s.trim().replace(' ', 'T')
  if (!/[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso)) iso += 'Z'
  return Date.parse(iso)
}

/**
 * 卫星网络态势大屏 3D 场景：
 * 真实卫星影像地球 + TLE 实时推算的真实轨道卫星（发光拖尾 + 50° 视锥体 + 名称标签）、
 * 5 个地面站（半球 + 旋转墙 + 站间连线）、
 * 3 颗 GEO 中继 + 星间橙色虚线链路 + 星地数传亮青链路。
 * 相机支持拖拽旋转 / 滚轮缩放 / 自动环绕（OrbitControls）。
 */
const SatelliteNetworkScene = forwardRef<NetworkSceneHandles, {
  satellites: SceneSatellite[]
  stations: SceneStation[]
  showTrails: boolean
  showCones: boolean
  showLinks: boolean
  /** 后端仿真时间（UTC 字符串），驱动 TLE 推算 */
  simTime: string
  /** 当前选中卫星 id（其视锥体单独显示） */
  selectedId?: number | null
  onSelect?: (id: number) => void
}>(({ satellites, stations, showTrails, showCones, showLinks, simTime, selectedId, onSelect }, ref) => {
  const hostRef = useRef<HTMLDivElement>(null)
  const nodesRef = useRef<Map<number, SatNode>>(new Map())
  const propsRef = useRef({ showTrails, showCones, showLinks, selectedId })
  propsRef.current = { showTrails, showCones, showLinks, selectedId }
  const satsRef = useRef(satellites)
  satsRef.current = satellites
  const stationsRef = useRef(stations)
  stationsRef.current = stations
  const simTimeRef = useRef(simTime)
  simTimeRef.current = simTime
  const flyTargetRef = useRef<number | null>(null)

  useImperativeHandle(ref, () => ({
    flyTo: (id: number) => { flyTargetRef.current = id },
  }))

  useEffect(() => {
    const host = hostRef.current!
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100)
    camera.position.set(0, 0.8, 4.2)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    host.appendChild(renderer.domElement)

    // 相机控制：拖拽旋转 + 滚轮缩放 + 缓慢自动环绕
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.enablePan = false
    controls.minDistance = 2.2
    controls.maxDistance = 9
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.5
    controls.addEventListener('start', () => { flyTargetRef.current = null })

    scene.add(new THREE.AmbientLight(0xbfd4f0, 1.5))
    const key = new THREE.DirectionalLight(0xcfeaff, 1.2)
    key.position.set(3, 2, 4)
    scene.add(key)
    const rim = new THREE.PointLight(0x1a9ae0, 6, 20)
    rim.position.set(-4, -2, -2)
    scene.add(rim)

    const world = new THREE.Group()
    world.rotation.y = 2.88 // 初始视角大致面向中国/亚太
    scene.add(world)

    // 真实卫星影像地球贴图（map + emissiveMap 提亮，对齐 Cesium 全亮观感）
    const earthTex = new THREE.TextureLoader().load(earthUrl)
    earthTex.colorSpace = THREE.SRGBColorSpace
    world.add(new THREE.Mesh(
      new THREE.SphereGeometry(1, 72, 72),
      new THREE.MeshPhongMaterial({
        map: earthTex,
        emissiveMap: earthTex,
        emissive: new THREE.Color(0xffffff),
        emissiveIntensity: 0.45,
        shininess: 12,
        specular: new THREE.Color(0x1a4a8a),
      }),
    ))
    world.add(glowSprite('rgba(50,180,255,0.4)', 2.85))

    const ensureNode = (sat_: SceneSatellite): SatNode | null => {
      const existing = nodesRef.current.get(sat_.id)
      if (existing) return existing
      if (!sat_.tle1 || !sat_.tle2) return null
      let satrec: sat.SatRec
      try {
        satrec = sat.twoline2satrec(sat_.tle1, sat_.tle2)
      } catch {
        return null
      }
      const color = SENSOR_COLOR[sat_.sensorType] ?? 0x00dcff

      const sprite = satelliteSprite(0.11)
      const glow = glowSprite('#7ceaff', 0.075)
      world.add(sprite); world.add(glow)

      // 视锥体（50° 开口，指向地心；单位高度，运行时按距离缩放）
      const cone = new THREE.Mesh(
        new THREE.ConeGeometry(Math.tan((25 * Math.PI) / 180), 1, 24, 1, true),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }),
      )
      world.add(cone)

      // 拖尾轨迹：真实轨道历史弧线（顶点渐隐由透明度体现，逐点重算）
      const trail = new THREE.Line(
        new THREE.BufferGeometry(),
        new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false }),
      )
      trail.frustumCulled = false
      world.add(trail)

      const label = labelSprite(sat_.name)
      world.add(label)

      const node: SatNode = { id: sat_.id, name: sat_.name, sensorType: sat_.sensorType, sprite, glow, cone, trail, label, satrec }
      nodesRef.current.set(sat_.id, node)
      return node
    }

    /** 按仿真时刻重算某颗卫星的拖尾轨迹（过去 35 分钟的真实轨道弧） */
    const trailPts: THREE.Vector3[] = []
    const updateTrail = (node: SatNode, simMs: number) => {
      trailPts.length = 0
      for (let i = TRAIL_POINTS; i >= 0; i--) {
        const d = new Date(simMs - i * TRAIL_STEP_MS)
        const pv = sat.propagate(node.satrec, d)
        const pos = pv && pv.position
        if (!pos || typeof pos === 'boolean') continue
        const g = sat.eciToGeodetic(pos, sat.gstime(d))
        trailPts.push(ll(sat.degreesLat(g.latitude), sat.degreesLong(g.longitude), 1 + g.height / EARTH_R_KM))
      }
      if (trailPts.length > 1) node.trail.geometry.setFromPoints(trailPts)
    }

    // 地面站（真实数据，来自 GET /satellites/groundStationInfo，异步到达后动态创建）
    const stationPos = new Map<string, THREE.Vector3>()
    const ensureStations = (list: SceneStation[]) => {
      for (const st of list) {
        if (stationPos.has(st.name)) continue
        const pos = ll(st.lat, st.lon, 1.01)
        const g = new THREE.Group()
        g.position.copy(pos)
        g.lookAt(0, 0, 0)

        const tower = stationSprite(0.12)
        tower.position.y = 0.01
        g.add(tower)

        // 300km 半径半球
        const dome = new THREE.Mesh(
          new THREE.SphereGeometry(0.07, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2),
          new THREE.MeshBasicMaterial({ color: 0x00c8ff, transparent: true, opacity: 0.1, side: THREE.DoubleSide, depthWrite: false }),
        )
        g.add(dome)
        const domeEdge = new THREE.LineSegments(
          new THREE.EdgesGeometry(new THREE.SphereGeometry(0.07, 24, 6, 0, Math.PI * 2, 0, Math.PI / 2)),
          new THREE.LineBasicMaterial({ color: 0x00dcff, transparent: true, opacity: 0.25 }),
        )
        g.add(domeEdge)

        // 旋转墙
        const wallGeo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0), new THREE.Vector3(0.07, 0.1, 0), new THREE.Vector3(-0.07, 0.1, 0),
        ])
        const wall = new THREE.Line(wallGeo, new THREE.LineBasicMaterial({ color: 0x4ff3ff, transparent: true, opacity: 0.5 }))
        wall.userData.spin = true
        g.add(wall)

        const pulse = glowSprite('rgba(79,243,255,0.8)', 0.08)
        pulse.userData.pulse = true
        g.add(pulse)

        world.add(g)
        stationPos.set(st.name, g.position)
      }
    }

    // GEO 高轨中继卫星（真实配置：高轨卫星1@东经120°、高轨卫星2@东经240°、高轨卫星3@0°，35786km 收在 2.1R）
    const geoMap = new Map<string, THREE.Sprite>()
    for (const g of GEO_SATS) {
      const s = satelliteSprite(0.14)
      s.position.copy(ll(0, g.lon, 2.1))
      world.add(s)
      const ring = orbitLine(2.1, 0xd88a2a, 0.18)
      ring.rotation.x = Math.PI / 2 - 0.02
      world.add(ring)
      geoMap.set(g.name, s)
    }

    // 真实链路线池：星间（卫星→GEO 橙色虚线）+ 星地数传（卫星→地面站 亮青实线），每帧按真实连接状态分配
    const LINK_POOL = 220
    const interLinks: THREE.Line[] = []
    for (let i = 0; i < LINK_POOL; i++) {
      const line = new THREE.Line(
        new THREE.BufferGeometry(),
        new THREE.LineDashedMaterial({ color: 0xff9d4d, dashSize: 0.04, gapSize: 0.03, transparent: true, opacity: 0.6 }),
      )
      line.visible = false
      world.add(line)
      interLinks.push(line)
    }
    const downLinks: THREE.Line[] = []
    for (let i = 0; i < LINK_POOL; i++) {
      const line = new THREE.Line(
        new THREE.BufferGeometry(),
        new THREE.LineBasicMaterial({ color: 0x4ff3ff, transparent: true, opacity: 0.75, blending: THREE.AdditiveBlending }),
      )
      line.visible = false
      world.add(line)
      downLinks.push(line)
    }

    // 射线拾取（拖拽后位移超过阈值则不触发选中）
    const raycaster = new THREE.Raycaster()
    raycaster.params.Sprite = { threshold: 0.06 }
    let downX = 0
    let downY = 0
    const onPointerDown = (e: PointerEvent) => { downX = e.clientX; downY = e.clientY }
    const onClick = (e: MouseEvent) => {
      if (Math.hypot(e.clientX - downX, e.clientY - downY) > 6) return
      const rect = renderer.domElement.getBoundingClientRect()
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      )
      raycaster.setFromCamera(mouse, camera)
      const sprites = [...nodesRef.current.values()].map((n) => n.sprite)
      const hits = raycaster.intersectObjects(sprites, false)
      if (hits.length && onSelectRef.current) {
        const node = [...nodesRef.current.values()].find((n) => n.sprite === hits[0].object)
        if (node) onSelectRef.current(node.id)
      }
    }
    renderer.domElement.addEventListener('pointerdown', onPointerDown)
    renderer.domElement.addEventListener('click', onClick)

    const onSelectRef = { current: onSelect }
    onSelectRef.current = onSelect

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = host
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(host)

    // 仿真时钟：以后端推送的 simTime 为基准，按实测速率外推（后端把时间字符串按 UTC 解释）
    const clock = { lastStr: '', base: Date.now(), wall: performance.now(), rate: 1 }

    let raf = 0
    let trailCursor = 0
    const v3 = new THREE.Vector3()
    const origin = new THREE.Vector3()
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const t = performance.now() / 1000
      const { showTrails: st, showCones: sc, showLinks: sl, selectedId: sel } = propsRef.current

      // 更新仿真时钟（simTime 每 5 秒由后端轮询刷新，期间按实测速率外推）
      const s = simTimeRef.current
      if (s && s !== clock.lastStr) {
        const ms = parseSimTime(s)
        if (!Number.isNaN(ms)) {
          const wallNow = performance.now()
          if (clock.lastStr) {
            const r = (ms - clock.base) / (wallNow - clock.wall)
            if (Number.isFinite(r) && r > 0.01 && r < 500) clock.rate = r
          }
          clock.base = ms; clock.wall = wallNow; clock.lastStr = s
        }
      }
      const simMs = clock.base + (performance.now() - clock.wall) * clock.rate
      const simDate = new Date(simMs)
      const gmst = sat.gstime(simDate)
      const camDist = camera.position.length()

      // 同步地面站（真实数据异步到达后补建）
      ensureStations(stationsRef.current)
      let downCount = 0
      let interCount = 0

      // 同步卫星节点：TLE 实时推算真实位置（ECI → 大地经纬度 → 场景坐标）
      satsRef.current.forEach((sat_) => {
        const node = ensureNode(sat_)
        if (!node) return
        const pv = sat.propagate(node.satrec, simDate)
        const pos = pv && pv.position
        if (!pos || typeof pos === 'boolean') {
          node.sprite.visible = false
          node.glow.visible = false
          node.cone.visible = false
          node.trail.visible = false
          node.label.visible = false
          return
        }
        const g = sat.eciToGeodetic(pos, gmst)
        const r = 1 + g.height / EARTH_R_KM
        const p = ll(sat.degreesLat(g.latitude), sat.degreesLong(g.longitude), r)
        node.sprite.position.copy(p)
        node.glow.position.copy(p)
        node.sprite.visible = sat_.visible
        node.glow.visible = sat_.visible
        node.glow.material.color.set(sat_.battery < 20 ? 0xff6a5a : 0x7ceaff)

        // 视锥体：顶端在卫星处，轴指向地心，长度截到地表/1000km
        const len = Math.min(r - 0.98, CONE_MAX_LEN)
        node.cone.visible = sat_.visible && len > 0 && (sc || sel === sat_.id)
        if (node.cone.visible) {
          node.cone.scale.setScalar(len)
          node.cone.position.copy(p).multiplyScalar((r - len / 2) / r)
          node.cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), p.clone().negate().normalize())
        }

        // 拖尾轨迹：相机拉近或选中时显示（对齐旧版 Cesium 距离显隐），几何由下方轮转账量重算
        node.trail.visible = sat_.visible && st && (camDist < 3.6 || sel === sat_.id)

        // 名称标签：相机拉近或聚焦时显示
        node.label.visible = sat_.visible && (camDist < LABEL_DIST || flyTargetRef.current != null)
        if (node.label.visible) node.label.position.copy(p).multiplyScalar((r + 0.07) / r)

        // 真实链路：星地数传（→相连地面站，亮青实线）、星间中继（→相连高轨卫星，橙色虚线）
        if (sl && sat_.visible) {
          const stPos = sat_.linkedStations.length ? stationPos.get(sat_.linkedStations[0]) : undefined
          if (stPos && downCount < downLinks.length) {
            const line = downLinks[downCount++]
            line.geometry.setFromPoints([p, stPos])
            line.visible = true
          }
          const geoSprite = geoMap.get(sat_.linkedGeo)
          if (geoSprite && camDist > 3.4 && interCount < interLinks.length) {
            const line = interLinks[interCount++]
            line.geometry.setFromPoints([p, geoSprite.position])
            line.computeLineDistances()
            line.visible = true
          }
        }
      })

      // 未分配出去的链路线隐藏
      for (let i = downCount; i < downLinks.length; i++) downLinks[i].visible = false
      for (let i = interCount; i < interLinks.length; i++) interLinks[i].visible = false

      // 拖尾重算轮转：每帧只更新 TRAILS_PER_FRAME 颗，分摊推算开销
      const allNodes = [...nodesRef.current.values()]
      if (allNodes.length) {
        for (let k = 0; k < TRAILS_PER_FRAME; k++) {
          trailCursor = (trailCursor + 1) % allNodes.length
          updateTrail(allNodes[trailCursor], simMs)
        }
      }

      // 旋转墙 + 呼吸点
      world.traverse((o) => {
        if (o.userData.spin) o.rotation.y = t * 2
        if (o.userData.pulse) o.scale.setScalar(0.07 + Math.abs(Math.sin(t * 2.4)) * 0.05)
      })

      // 相机：flyTo 或自由环绕
      const targetId = flyTargetRef.current
      if (targetId != null && nodesRef.current.has(targetId)) {
        const node = nodesRef.current.get(targetId)!
        node.sprite.getWorldPosition(v3)
        controls.autoRotate = false
        controls.target.lerp(v3, 0.08)
        camera.position.lerp(v3.clone().multiplyScalar(2.8 / v3.length()), 0.06)
      } else {
        controls.autoRotate = true
        controls.target.lerp(origin, 0.05)
      }
      controls.update()

      renderer.render(scene, camera)
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      controls.dispose()
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('click', onClick)
      renderer.dispose()
      host.removeChild(renderer.domElement)
      nodesRef.current.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="relative h-full w-full">
      <div ref={hostRef} className="absolute inset-0" />
      {/* 中央雷达环 + 十字线装饰（双环反向旋转） */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="relative h-[68%] w-[68%] opacity-30">
          <div className="radar-spin absolute inset-0 rounded-full border border-dashed border-[rgba(0,220,255,0.4)]" />
          <div className="radar-spin-fast absolute inset-[12%] rounded-full border border-dashed border-[rgba(0,220,255,0.3)]" />
          <div className="absolute left-1/2 top-0 h-full w-px bg-gradient-to-b from-transparent via-[rgba(0,220,255,0.35)] to-transparent" />
          <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-[rgba(0,220,255,0.35)] to-transparent" />
        </div>
      </div>
    </div>
  )
})

SatelliteNetworkScene.displayName = 'SatelliteNetworkScene'
export default SatelliteNetworkScene
