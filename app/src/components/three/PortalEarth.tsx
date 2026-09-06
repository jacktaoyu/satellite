import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { createEarthTexture } from './earthTexture'
import { ll, arc, glowSprite, satelliteSprite, stationSprite, orbitLine } from './common'

/**
 * 门户页 3D 地球：
 * 自转 + 视角摆动 + 5 颗绕轨发光卫星 + 3 个地面站呼吸光点 + 星地光束。
 */
export default function PortalEarth() {
  const hostRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const host = hostRef.current!
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100)
    camera.position.set(0, 0.5, 4.6)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    host.appendChild(renderer.domElement)

    scene.add(new THREE.AmbientLight(0x8fb8e8, 1.0))
    const key = new THREE.DirectionalLight(0xcfeaff, 2.4)
    key.position.set(3, 2, 4)
    scene.add(key)
    const rim = new THREE.PointLight(0x1a9ae0, 8, 20)
    rim.position.set(-4, -1, -2)
    scene.add(rim)

    const world = new THREE.Group()
    world.rotation.y = 2.6
    scene.add(world)

    // 地球 + 大气
    world.add(new THREE.Mesh(
      new THREE.SphereGeometry(1, 72, 72),
      new THREE.MeshPhongMaterial({ map: new THREE.CanvasTexture(createEarthTexture()), shininess: 14, specular: new THREE.Color(0x1a5a9a) }),
    ))
    const halo = glowSprite('rgba(60,190,255,0.5)', 3.0)
    world.add(halo)

    // 轨道环 + 5 颗装饰卫星
    const orbits: { group: THREE.Group; sats: { s: THREE.Sprite; a: number; v: number }[] }[] = []
    const cfg = [
      { r: 1.35, tx: 0.5, tz: 0.1, n: 2 },
      { r: 1.6, tx: 0.4, tz: -0.25, n: 2 },
      { r: 1.85, tx: 0.62, tz: 0.35, n: 1 },
    ]
    for (const c of cfg) {
      const g = new THREE.Group()
      g.rotation.x = c.tx
      g.rotation.z = c.tz
      g.add(orbitLine(c.r, 0x3ec8ff, 0.55))
      const glow = orbitLine(c.r, 0x3ec8ff, 0.15)
      glow.scale.setScalar(1.001)
      g.add(glow)
      const sats: { s: THREE.Sprite; a: number; v: number }[] = []
      for (let i = 0; i < c.n; i++) {
        const s = satelliteSprite(0.22)
        const glow = glowSprite('rgba(120,230,255,0.9)', 0.12)
        g.add(s); g.add(glow)
        sats.push({ s, a: (i / c.n) * Math.PI * 2 + Math.random(), v: 0.16 + Math.random() * 0.08 })
        // 将光晕挂到卫星同一位置：通过每帧同步
        s.userData.glow = glow
      }
      world.add(g)
      orbits.push({ group: g, sats })
    }

    // 地面站 + 呼吸光点 + 星地光束
    const stations = [
      { name: '北京', lat: 39.9, lon: 116.4 },
      { name: '喀什', lat: 39.5, lon: 76.0 },
      { name: '三亚', lat: 18.3, lon: 109.5 },
    ]
    const beams: THREE.Line[] = []
    stations.forEach((st, i) => {
      const pos = ll(st.lat, st.lon, 1.02)
      const tower = stationSprite(0.14)
      tower.position.copy(pos)
      world.add(tower)
      const pulse = glowSprite('rgba(79,243,255,0.9)', 0.12)
      pulse.position.copy(pos)
      pulse.userData.pulse = true
      world.add(pulse)
      // 光束连到第一颗卫星（每帧更新）
      const geo = new THREE.BufferGeometry().setFromPoints(new Array(26).fill(0).map(() => new THREE.Vector3()))
      const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0x4ff3ff, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending }))
      line.userData = { stationPos: pos, satIdx: i }
      world.add(line)
      beams.push(line)
    })

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = host
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(host)

    // 鼠标视差
    let mx = 0, my = 0
    const onMove = (e: MouseEvent) => {
      mx = (e.clientX / innerWidth - 0.5) * 0.3
      my = (e.clientY / innerHeight - 0.5) * 0.2
    }
    window.addEventListener('mousemove', onMove)

    let raf = 0
    const v3 = new THREE.Vector3()
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const t = performance.now() / 1000
      world.rotation.y += 0.0012

      // 相机在亚洲昼半球 ±20° 摆动 + 视差
      const swing = Math.sin(t * 0.15) * 0.35
      camera.position.x = swing * 0.5 + mx
      camera.position.y = 0.5 + my
      camera.lookAt(0, 0, 0)

      // 卫星巡游
      const allSats: THREE.Sprite[] = []
      for (const ob of orbits) {
        for (const st of ob.sats) {
          st.a += st.v * 0.008
          const r = ob.group.children.length ? (orbitRadiusOf(ob.group)) : 1.5
          st.s.position.set(Math.cos(st.a) * r, 0, Math.sin(st.a) * r)
          ;(st.s.userData.glow as THREE.Sprite).position.copy(st.s.position)
          allSats.push(st.s)
        }
      }
      // 星地光束
      beams.forEach((beam) => {
        const sat = allSats[beam.userData.satIdx % allSats.length]
        sat.getWorldPosition(v3)
        world.worldToLocal(v3)
        beam.geometry.setFromPoints(arc(v3, beam.userData.stationPos, 0.1, 24))
      })
      // 呼吸光点
      world.traverse((o) => {
        if (o.userData.pulse) {
          const s = 0.1 + Math.abs(Math.sin(t * 2)) * 0.06
          o.scale.setScalar(s)
        }
      })

      renderer.render(scene, camera)
    }
    // 轨道半径缓存
    function orbitRadiusOf(g: THREE.Group): number {
      const line = g.children[0] as THREE.Line
      const pos = (line.geometry as THREE.BufferGeometry).getAttribute('position')
      return Math.hypot(pos.getX(0), pos.getZ(0))
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      window.removeEventListener('mousemove', onMove)
      renderer.dispose()
      host.removeChild(renderer.domElement)
    }
  }, [])

  return <div ref={hostRef} className="absolute inset-0" />
}
