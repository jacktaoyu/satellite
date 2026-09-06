import { useState } from 'react'
import { useNavigate, Link } from 'react-router'
import { User, Lock, Users } from 'lucide-react'
import { login } from '@/api'

/** 登录卡片（登录页 / 门户弹层复用） */
export default function LoginCard({ onSuccess }: { onSuccess?: () => void }) {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('管理员')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (loading) return
    setError('')
    setLoading(true)
    // POST /login/
    const res = await login({ username, password, value: role })
    setLoading(false)
    if (res.code === 200) {
      onSuccess?.()
      navigate('/satellite/satellite_network')
    } else {
      setError(res.msg ?? '登录失败')
    }
  }

  return (
    <div className="tech-panel w-[340px] p-6">
      <div className="mb-1 text-lg font-bold tracking-[0.3em] text-[#e0f6ff]" style={{ textShadow: '0 0 16px rgba(0,220,255,0.6)' }}>
        用户登录
      </div>
      <div className="mb-5 text-[10px] tracking-[0.2em] text-[#3d6491]">SATELLITE CLUSTER COLLABORATIVE PLATFORM</div>

      <div className="space-y-3">
        <div className="relative">
          <User size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#3d6491]" />
          <input className="tech-input w-full !pl-8" placeholder="账号" value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div className="relative">
          <Lock size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#3d6491]" />
          <input
            className="tech-input w-full !pl-8" type="password" placeholder="密码（不少于 6 位）"
            value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </div>
        <div className="relative">
          <Users size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#3d6491]" />
          <select className="tech-input w-full !pl-8" value={role} onChange={(e) => setRole(e.target.value)}>
            <option>管理员</option>
            <option>用户</option>
          </select>
        </div>
        {error && <div className="text-[11px] text-[#ff8d8d]">{error}</div>}
        <button onClick={submit} disabled={loading} className="tech-btn w-full !py-2 text-sm tracking-[0.6em]">
          {loading ? '登录中…' : '登 录'}
        </button>
        <div className="text-right text-[11px] text-[#5d8cb8]">
          还没有账号？<Link to="/register" className="text-[#4fd8ff] hover:underline">立即注册</Link>
        </div>
      </div>
    </div>
  )
}
