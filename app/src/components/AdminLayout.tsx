import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router'
import {
  Globe2, Settings, Satellite, ClipboardList, ClipboardPlus, Boxes, RadioTower, FlaskConical, BarChart3,
  PanelLeftClose, PanelLeftOpen, User, ChevronDown, LogOut, KeyRound, Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Modal, FormRow } from '@/components/ui/widgets'
import { clearToken, updatePassword } from '@/api'

const MENU = [
  { group: '态势监控', items: [{ to: '/satellite/satellite_network', label: '卫星网络', icon: Globe2 }] },
  {
    group: '资源管理',
    items: [
      { to: '/satellite/weixing', label: '卫星管理', icon: Satellite },
      { to: '/satellite/xingcu', label: '星簇管理', icon: Boxes },
      { to: '/satellite/ground_station', label: '地面站', icon: RadioTower },
    ],
  },
  {
    group: '任务调度',
    items: [
      { to: '/satellite/renwu/shuxing', label: '任务属性', icon: ClipboardList },
      { to: '/satellite/renwu/shezhi', label: '任务设置', icon: ClipboardPlus },
      { to: '/satellite/yongli', label: '示范用例', icon: FlaskConical },
    ],
  },
  {
    group: '评估与配置',
    items: [
      { to: '/satellite/xingneng', label: '性能分析', icon: BarChart3 },
      { to: '/satellite/system_settings', label: '系统设置', icon: Settings },
    ],
  },
]

export default function AdminLayout() {
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)
  const [userMenu, setUserMenu] = useState(false)
  const [pwdOpen, setPwdOpen] = useState(false)
  const [pwd, setPwd] = useState({ account: '', next: '', confirm: '' })
  const [pwdMsg, setPwdMsg] = useState('')

  const userInfo = JSON.parse(localStorage.getItem('userInfo') ?? '{"nickname":"访客","role":"user"}')

  // 顶栏实时时钟
  const [clock, setClock] = useState('')
  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    tick()
    const t = setInterval(tick, 1000)
    return () => clearInterval(t)
  }, [])

  const logout = () => {
    clearToken()
    localStorage.removeItem('userInfo')
    navigate('/login')
  }

  const submitPwd = async () => {
    setPwdMsg('')
    if (!pwd.next || pwd.next !== pwd.confirm) {
      setPwdMsg('两次输入的新密码不一致')
      return
    }
    // POST /updatePassword
    await updatePassword({ username: pwd.account, password: pwd.next })
    setPwdMsg('修改成功')
    setTimeout(() => setPwdOpen(false), 800)
  }

  return (
    <div className="flex h-full">
      {/* 侧边栏 */}
      <aside
        className="flex shrink-0 flex-col border-r border-[rgba(0,200,255,0.18)] bg-[rgba(3,12,32,0.85)] transition-all duration-200"
        style={{ width: collapsed ? 56 : 200 }}
      >
        {!collapsed && (
          <div className="border-b border-[rgba(0,200,255,0.15)] px-4 py-4">
            <div className="flex items-center gap-3">
              <span className="relative flex h-8 w-8 shrink-0 items-center justify-center">
                <Satellite size={17} className="text-[#4ff3ff]" style={{ filter: 'drop-shadow(0 0 6px rgba(79,243,255,0.8))' }} />
                <i className="radar-ring" />
                <i className="radar-ring-outer" />
              </span>
              <div className="text-[12px] font-bold leading-4 tracking-wider text-[#e0f6ff]" style={{ textShadow: '0 0 10px rgba(0,220,255,0.4)' }}>
                智能星簇协同运行<br />验证系统
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1.5 text-[9px] tracking-[0.25em] text-[#3d6491]">
              <Activity size={9} className="text-[#4fe3a5]" />
              SATELLITE CLUSTER PLATFORM
            </div>
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-y-auto py-2">
          {MENU.map((g) => (
            <div key={g.group}>
              {!collapsed && <div className="nav-group">{g.group}</div>}
              {g.items.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} title={label} className={({ isActive }) => cn('nav-item text-[13px]', isActive && 'active', collapsed && '!justify-center !px-0')}>
                  <Icon size={15} className="shrink-0" />
                  {!collapsed && <span>{label}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
      </aside>

      {/* 主区 */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* 顶栏 */}
        <header className="relative flex h-11 shrink-0 items-center justify-between border-b border-[rgba(0,200,255,0.18)] bg-[rgba(4,16,40,0.7)] px-3">
          <div className="flex min-w-0 flex-1 items-center">
            <button onClick={() => setCollapsed(!collapsed)} className="text-[#7ea6d8] hover:text-[#4fd8ff]">
              {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
            </button>
            <div className="header-deco" />
          </div>

          <div className="mr-4 hidden items-center gap-4 md:flex">
            <span className="flex items-center gap-1.5 text-[10px] text-[#4fe3a5]">
              <i className="dot animate-blink" style={{ background: '#4fe3a5', boxShadow: '0 0 5px #4fe3a5' }} />
              链路正常
            </span>
            <span className="num-font text-[11px] tracking-wider text-[#4fd8ff]" style={{ textShadow: '0 0 8px rgba(0,220,255,0.5)' }}>{clock}</span>
          </div>

          <div className="relative">
            <button onClick={() => setUserMenu(!userMenu)} className="flex items-center gap-2 text-xs text-[#b8d8f0] hover:text-[#4fd8ff]">
              <span className="flex h-6 w-6 items-center justify-center rounded-full border border-[rgba(0,220,255,0.5)] bg-[rgba(0,140,240,0.25)]">
                <User size={13} className="text-[#4ff3ff]" />
              </span>
              {userInfo.nickname}
              <ChevronDown size={12} />
            </button>
            {userMenu && (
              <div className="tech-panel absolute right-0 top-9 z-40 w-36 py-1 text-xs" onMouseLeave={() => setUserMenu(false)}>
                <div className="cursor-not-allowed px-3 py-2 text-[#3d6491]">个人中心</div>
                <button
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-[#b8d8f0] hover:bg-[rgba(0,160,255,0.12)]"
                  onClick={() => { setUserMenu(false); setPwdOpen(true) }}
                >
                  <KeyRound size={12} /> 个人设置
                </button>
                <button className="flex w-full items-center gap-2 px-3 py-2 text-left text-[#ff9d9d] hover:bg-[rgba(255,80,80,0.1)]" onClick={logout}>
                  <LogOut size={12} /> 退出登录
                </button>
              </div>
            )}
          </div>
        </header>

        {/* 内容 */}
        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={pwdOpen}
        onClose={() => setPwdOpen(false)}
        width={380}
        footer={
          <>
            <button className="tech-btn-ghost" onClick={() => setPwdOpen(false)}>取消</button>
            <button className="tech-btn" onClick={submitPwd}>确认修改</button>
          </>
        }
      >
        <div className="space-y-3">
          <FormRow label="账号" required><input className="tech-input w-full" value={pwd.account} onChange={(e) => setPwd({ ...pwd, account: e.target.value })} /></FormRow>
          <FormRow label="新密码" required><input type="password" className="tech-input w-full" value={pwd.next} onChange={(e) => setPwd({ ...pwd, next: e.target.value })} /></FormRow>
          <FormRow label="确认密码" required><input type="password" className="tech-input w-full" value={pwd.confirm} onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })} /></FormRow>
          {pwdMsg && <div className={cn('text-[11px]', pwdMsg === '修改成功' ? 'text-[#4fe3a5]' : 'text-[#ff8d8d]')}>{pwdMsg}</div>}
        </div>
      </Modal>
    </div>
  )
}
