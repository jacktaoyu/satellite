import { Link } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import PortalEarth from '@/components/three/PortalEarth'
import Starfield from '@/components/effects/Starfield'
import LoginCard from '@/components/LoginCard'

export default function Login() {
  return (
    <div className="relative h-full overflow-hidden">
      <div className="absolute inset-0 opacity-70">
        <PortalEarth />
      </div>
      <Starfield density={60} />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,rgba(2,8,26,0.75)_100%)]" />

      <Link to="/portal" className="absolute left-5 top-5 z-10 flex items-center gap-1.5 text-xs text-[#7ea6d8] hover:text-[#4fd8ff]">
        <ArrowLeft size={14} /> 返回首页
      </Link>

      <div className="relative z-10 flex h-full items-center justify-center gap-16 px-8">
        {/* 左侧标语区（窄屏隐藏） */}
        <div className="hidden max-w-md lg:block">
          <div className="mb-3 inline-block border border-[rgba(0,220,255,0.4)] px-3 py-1 text-[10px] tracking-[0.3em] text-[#4fd8ff]">
            SATELLITE CLUSTER COLLABORATIVE PLATFORM
          </div>
          <h1 className="text-4xl font-bold leading-snug text-[#e0f6ff]" style={{ textShadow: '0 0 24px rgba(0,220,255,0.5)' }}>
            智能星簇
            <br />
            协同运行验证系统
          </h1>
          <p className="mt-4 text-sm text-[#7ea6d8]">三维组网可视化 · 任务协同规划 · 运行效能评估</p>
        </div>
        <LoginCard />
      </div>
    </div>
  )
}
