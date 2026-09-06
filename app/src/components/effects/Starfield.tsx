import { useEffect, useRef } from 'react'

/** Canvas 星空 + 流星粒子背景层 */
export default function Starfield({ density = 90 }: { density?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current!
    const ctx = canvas.getContext('2d')!
    let w = 0, h = 0, raf = 0

    const resize = () => {
      w = canvas.width = canvas.offsetWidth * devicePixelRatio
      h = canvas.height = canvas.offsetHeight * devicePixelRatio
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    const stars = Array.from({ length: density }, () => ({
      x: Math.random(), y: Math.random(),
      r: Math.random() * 1.2 + 0.3,
      p: Math.random() * Math.PI * 2,
      s: 0.5 + Math.random(),
    }))
    let meteors: { x: number; y: number; vx: number; vy: number; life: number }[] = []

    const tick = () => {
      raf = requestAnimationFrame(tick)
      ctx.clearRect(0, 0, w, h)
      const t = performance.now() / 1000

      // 星星闪烁
      for (const s of stars) {
        const a = 0.25 + 0.55 * Math.abs(Math.sin(t * s.s + s.p))
        ctx.beginPath()
        ctx.arc(s.x * w, s.y * h, s.r * devicePixelRatio, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(180,225,255,${a})`
        ctx.fill()
      }

      // 流星
      if (Math.random() < 0.008 && meteors.length < 2) {
        meteors.push({ x: Math.random() * w * 0.8, y: Math.random() * h * 0.3, vx: 6 * devicePixelRatio, vy: 2.4 * devicePixelRatio, life: 1 })
      }
      meteors = meteors.filter((m) => m.life > 0)
      for (const m of meteors) {
        m.x += m.vx; m.y += m.vy; m.life -= 0.02
        const g = ctx.createLinearGradient(m.x - m.vx * 10, m.y - m.vy * 10, m.x, m.y)
        g.addColorStop(0, 'rgba(0,220,255,0)')
        g.addColorStop(1, `rgba(160,235,255,${0.7 * m.life})`)
        ctx.strokeStyle = g
        ctx.lineWidth = 1.4 * devicePixelRatio
        ctx.beginPath()
        ctx.moveTo(m.x - m.vx * 10, m.y - m.vy * 10)
        ctx.lineTo(m.x, m.y)
        ctx.stroke()
      }
    }
    tick()

    return () => { cancelAnimationFrame(raf); ro.disconnect() }
  }, [density])

  return <canvas ref={ref} className="pointer-events-none absolute inset-0 h-full w-full" />
}
