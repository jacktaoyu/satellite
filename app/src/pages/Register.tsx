import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import Starfield from '@/components/effects/Starfield'
import { register } from '@/api'

export default function Register() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setError('')
    if (username.length < 3 || username.length > 20) return setError('用户名需为 3-20 个字符')
    if (password.length < 6) return setError('密码不少于 6 位')
    if (password !== confirm) return setError('两次输入的密码不一致')
    setLoading(true)
    // POST /register/
    const res = await register({ username, password })
    setLoading(false)
    if (res.code === 200) navigate('/login')
    else setError(res.msg ?? '注册失败')
  }

  return (
    <div className="relative flex h-full items-center justify-center overflow-hidden">
      <Starfield density={70} />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,90,190,0.12),rgba(2,8,26,0.85)_80%)]" />
      <div className="tech-panel relative z-10 w-[360px] p-6" style={{ background: 'rgba(8, 22, 48, 0.75)' }}>
        <div className="mb-1 text-lg font-bold tracking-[0.3em] text-[#e0f6ff]" style={{ textShadow: '0 0 16px rgba(0,220,255,0.6)' }}>用户注册</div>
        <div className="mb-5 text-[10px] tracking-[0.2em] text-[#3d6491]">注册后默认为普通用户</div>
        <div className="space-y-3">
          <input className="tech-input w-full" placeholder="用户名（3-20 字符）" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input className="tech-input w-full" type="password" placeholder="密码（不少于 6 位）" value={password} onChange={(e) => setPassword(e.target.value)} />
          <input className="tech-input w-full" type="password" placeholder="确认密码" value={confirm} onChange={(e) => setConfirm(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} />
          {error && <div className="text-[11px] text-[#ff8d8d]">{error}</div>}
          <button onClick={submit} disabled={loading} className="tech-btn w-full !py-2 text-sm tracking-[0.6em]">
            {loading ? '注册中…' : '注 册'}
          </button>
          <div className="text-right text-[11px] text-[#5d8cb8]">
            已有账号？<Link to="/login" className="text-[#4fd8ff] hover:underline">返回登录</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
