import { useEffect, useState } from 'react'
import { ArrowRight, Satellite, ClipboardList, Hourglass, MonitorCheck } from 'lucide-react'
import PortalEarth from '@/components/three/PortalEarth'
import Starfield from '@/components/effects/Starfield'
import LoginCard from '@/components/LoginCard'
import { getStatistics } from '@/api'

/** 数字滚动动画 */
function CountUp({ value }: { value: number }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    const start = performance.now()
    const dur = 1400
    let raf = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / dur)
      setDisplay(Math.round(value * (1 - Math.pow(1 - t, 3))))
      if (t < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <>{display.toLocaleString()}</>
}

export default function Portal() {
  const [stats, setStats] = useState({ satellites: 0, todayTasks: 0, pendingTasks: 0, clients: 0 })
  const [showLogin, setShowLogin] = useState(false)
  const [zooming, setZooming] = useState(false)

  useEffect(() => {
    // GET /statistics
    getStatistics().then(setStats)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowLogin(false)
        setZooming(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const enter = () => {
    setZooming(true)
    setTimeout(() => setShowLogin(true), 550)
  }
  const closeLogin = () => {
    setShowLogin(false)
    setZooming(false)
  }

  const cards = [
    { icon: Satellite, label: '在轨卫星', value: stats.satellites, unit: '颗' },
    { icon: ClipboardList, label: '今日任务', value: stats.todayTasks, unit: '次' },
    { icon: Hourglass, label: '待执行任务', value: stats.pendingTasks, unit: '次' },
    { icon: MonitorCheck, label: '在线客户端', value: stats.clients, unit: '个' },
  ]

  return (
    <div className="relative h-full overflow-hidden">
      {/* 3D 地球背景 + 星空 */}
      <div
        className="absolute inset-0 transition-transform duration-700 ease-in-out"
        style={{ transform: zooming ? 'scale(1.35)' : 'scale(1)' }}
      >
        <PortalEarth />
      </div>
      <Starfield />

      {/* 扫描线 + HUD 四角框 */}
      <div className="scan-deco pointer-events-none absolute inset-0" />
      {['top-3 left-3 border-t-2 border-l-2', 'top-3 right-3 border-t-2 border-r-2', 'bottom-3 left-3 border-b-2 border-l-2', 'bottom-3 right-3 border-b-2 border-r-2'].map((c) => (
        <i key={c} className={`pointer-events-none absolute h-6 w-6 border-[#00dcff]/60 ${c}`} />
      ))}

      {/* 遥测读数装饰 */}
      <div className="pointer-events-none absolute right-6 top-24 hidden space-y-1 text-right text-[10px] leading-4 text-[#3d6491] lg:block">
        <div>ALT 500.00 KM</div><div>INC 97.40°</div><div>VEL 7.61 KM/S</div><div>SYN ●●●●○</div>
      </div>

      {/* 顶部导航 */}
      <header className="relative z-10 flex h-14 items-center justify-between border-b border-[rgba(0,200,255,0.15)] bg-[rgba(2,8,26,0.4)] px-6 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Satellite size={20} className="text-[#4ff3ff]" />
          <span className="text-[15px] font-bold tracking-[0.2em] text-[#e0f6ff]" style={{ textShadow: '0 0 12px rgba(0,220,255,0.5)' }}>
            智能星簇协同运行验证系统
          </span>
        </div>
        <button onClick={enter} className="tech-btn flex items-center gap-1.5 !px-4">
          进入系统 <ArrowRight size={13} />
        </button>
      </header>

      {/* Hero 区 */}
      <div className="relative z-10 flex h-[calc(100%-56px-44px)] items-center">
        <div className="w-full max-w-xl pl-10 lg:pl-16">
          <div className="mb-4 inline-flex items-center gap-2 border border-[rgba(0,220,255,0.4)] bg-[rgba(0,150,255,0.08)] px-3 py-1 text-[10px] tracking-[0.3em] text-[#4fd8ff] animate-float">
            ● SATELLITE CLUSTER COLLABORATIVE PLATFORM
          </div>
          <h1 className="text-[44px] font-bold leading-tight tracking-wide text-[#e0f6ff]" style={{ textShadow: '0 0 30px rgba(0,220,255,0.55), 0 0 60px rgba(0,140,255,0.3)' }}>
            智能星簇
            <br />
            协同运行验证系统
          </h1>
          <p className="mt-4 text-sm leading-6 text-[#7ea6d8]">
            面向卫星集群在轨运行的三维可视化监控、任务协同规划与效能评估验证平台。
            支持 TLE 轨道推演、多算法调度对比与全生命周期任务管理。
          </p>
          <button onClick={enter} className="tech-btn mt-6 flex items-center gap-2 !px-6 !py-2.5 !text-sm">
            进入系统 <ArrowRight size={15} />
          </button>

          {/* 数据看板 */}
          <div className="mt-10 grid grid-cols-4 gap-3">
            {cards.map(({ icon: Icon, label, value, unit }) => (
              <div key={label} className="stat-card">
                <Icon size={16} className="mb-1.5 text-[#4fd8ff]" />
                <div className="num-font text-2xl font-bold glow-text">
                  <CountUp value={value} />
                  <span className="ml-0.5 text-[10px] font-normal text-[#7ea6d8]">{unit}</span>
                </div>
                <div className="mt-0.5 text-[10px] text-[#5d8cb8]">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 页脚 */}
      <footer className="absolute bottom-0 z-10 flex h-11 w-full items-center justify-center border-t border-[rgba(0,200,255,0.12)] text-[11px] text-[#3d6491]">
        © 2026 智能星簇协同运行验证系统 · Satellite Cluster Collaborative Platform
      </footer>

      {/* 登录弹层 */}
      {showLogin && (
        <div className="modal-mask" onClick={closeLogin}>
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button onClick={closeLogin} className="absolute -right-2 -top-2 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-[rgba(0,220,255,0.5)] bg-[#04122c] text-[#7ea6d8] hover:text-white">
              ✕
            </button>
            <LoginCard />
          </div>
        </div>
      )}
    </div>
  )
}
