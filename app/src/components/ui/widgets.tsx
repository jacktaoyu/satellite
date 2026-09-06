import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/** 顶部统计卡 */
export function StatCard({
  icon: Icon, label, value, unit, tone = 'cyan',
}: {
  icon: LucideIcon
  label: string
  value: number | string
  unit?: string
  tone?: 'cyan' | 'red' | 'green' | 'amber' | 'violet'
}) {
  const colors = {
    cyan: '#4ff3ff', red: '#ff7a7a', green: '#4fe3a5', amber: '#ffc94d', violet: '#b89dff',
  }
  const c = colors[tone]
  return (
    <div className="stat-card flex items-center gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center border" style={{ borderColor: `${c}55`, background: `${c}14`, boxShadow: `inset 0 0 10px ${c}22` }}>
        <Icon size={18} style={{ color: c }} />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] text-[#5d8cb8]">{label}</div>
        <div className="num-font text-xl font-bold leading-tight" style={{ color: c, textShadow: `0 0 10px ${c}66` }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
          {unit && <span className="ml-1 text-[10px] font-normal text-[#7ea6d8]">{unit}</span>}
        </div>
      </div>
    </div>
  )
}

/** 彩色徽标 */
export function Tag({ text, tone = 'cyan' }: { text: string; tone?: 'cyan' | 'green' | 'red' | 'amber' | 'violet' | 'gray' }) {
  const map = {
    cyan: 'text-[#4fd8ff] border-[rgba(0,210,255,0.45)] bg-[rgba(0,190,255,0.1)]',
    green: 'text-[#4fe3a5] border-[rgba(70,220,160,0.45)] bg-[rgba(50,200,140,0.1)]',
    red: 'text-[#ff8d8d] border-[rgba(255,100,100,0.5)] bg-[rgba(255,80,80,0.12)]',
    amber: 'text-[#ffc94d] border-[rgba(255,200,80,0.45)] bg-[rgba(255,190,60,0.1)]',
    violet: 'text-[#b89dff] border-[rgba(160,120,255,0.45)] bg-[rgba(140,100,255,0.12)]',
    gray: 'text-[#6d93c4] border-[rgba(110,150,210,0.35)] bg-[rgba(90,130,190,0.1)]',
  }
  return <span className={cn('inline-block border px-1.5 py-px text-[10px] leading-4', map[tone])}>{text}</span>
}

/** 载荷类型 → 颜色 */
export const sensorTone = (s: string): 'cyan' | 'amber' | 'green' => (s === '光学' ? 'cyan' : s === '红外' ? 'amber' : 'green')
/** 任务状态 → 颜色 */
export const taskStatusTone = (s: string): 'green' | 'gray' | 'amber' | 'cyan' =>
  (s === '执行中' ? 'green' : s === '已完成' ? 'gray' : s === '暂停' ? 'amber' : 'cyan')

/** 状态点 */
export function StatusDot({ color, label, value }: { color: string; label: string; value?: string | number }) {
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-[#8fb8e8]">
      <i className="dot" style={{ background: color, boxShadow: `0 0 5px ${color}` }} />
      {label}
      {value !== undefined && <span className="num-font text-[#d8f2ff]">{value}</span>}
    </span>
  )
}

/** 进度条 */
export function Progress({ value, color = '#00dcff', className }: { value: number; color?: string; className?: string }) {
  return (
    <div className={cn('h-1.5 w-full bg-[rgba(0,140,220,0.15)]', className)}>
      <div
        className="h-full transition-all duration-500"
        style={{ width: `${Math.min(100, value)}%`, background: `linear-gradient(90deg, ${color}55, ${color})`, boxShadow: `0 0 6px ${color}88` }}
      />
    </div>
  )
}

/** 开关 */
export function Switch({ checked, onChange, size = 'md' }: { checked: boolean; onChange?: (v: boolean) => void; size?: 'sm' | 'md' }) {
  const w = size === 'sm' ? 'w-7 h-4' : 'w-9 h-5'
  const d = size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'
  return (
    <button
      onClick={() => onChange?.(!checked)}
      className={cn('relative shrink-0 rounded-full border transition-all', w)}
      style={{
        background: checked ? 'rgba(0,190,255,0.4)' : 'rgba(60,90,130,0.4)',
        borderColor: checked ? 'rgba(0,220,255,0.7)' : 'rgba(90,130,180,0.4)',
        boxShadow: checked ? '0 0 8px rgba(0,220,255,0.4)' : 'none',
      }}
    >
      <i className={cn('absolute top-1/2 -translate-y-1/2 rounded-full bg-white transition-all', d)}
        style={{ left: checked ? 'calc(100% - 18px)' : '2px', background: checked ? '#4ff3ff' : '#7ea6d8' }} />
    </button>
  )
}

/** 分页（传 onPageSizeChange 时显示「每页 N 条」下拉） */
export function Pagination({
  page, total, pageSize, onChange, onPageSizeChange, pageSizeOptions = [8, 10, 20, 50],
}: {
  page: number
  total: number
  pageSize: number
  onChange: (p: number) => void
  onPageSizeChange?: (n: number) => void
  pageSizeOptions?: number[]
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="flex items-center justify-end gap-1.5 pt-2 text-[11px] text-[#5d8cb8]">
      <span>共 {total} 条</span>
      {Array.from({ length: pages }, (_, i) => i + 1).slice(0, 8).map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            'h-5 min-w-5 border px-1',
            p === page
              ? 'border-[rgba(0,220,255,0.7)] bg-[rgba(0,180,255,0.35)] text-[#e0f6ff]'
              : 'border-[rgba(0,200,255,0.2)] hover:text-[#9fe8ff]',
          )}
        >
          {p}
        </button>
      ))}
      {onPageSizeChange && (
        <select
          className="tech-input ml-1 h-5 !w-auto !py-0 px-1 text-[11px]"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {pageSizeOptions.map((n) => <option key={n} value={n}>每页 {n} 条</option>)}
        </select>
      )}
    </div>
  )
}

/** 弹窗 */
export function Modal({
  title, open, onClose, children, width = 560, footer,
}: {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
  width?: number
  footer?: ReactNode
}) {
  if (!open) return null
  return (
    <div className="modal-mask" onClick={onClose}>
      <div
        className="tech-panel max-h-[85vh] overflow-y-auto"
        style={{ width, maxWidth: '92vw' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[rgba(0,200,255,0.18)] px-4 py-2.5">
          <div className="panel-title">{title}</div>
          <button onClick={onClose} className="text-[#5d8cb8] hover:text-white">✕</button>
        </div>
        <div className="px-4 py-3">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-[rgba(0,200,255,0.14)] px-4 py-2.5">{footer}</div>}
      </div>
    </div>
  )
}

/** 表单行 */
export function FormRow({ label, required, children }: { label: string; required?: boolean; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-[11px]">
      <span className="text-[#7ea6d8]">
        {required && <i className="mr-0.5 not-italic text-[#ff7a7a]">*</i>}
        {label}
      </span>
      {children}
    </label>
  )
}

/** 页面标题头（后台页面统一） */
export function PageHeader({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="tech-panel scan-deco mb-3 flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-3">
        {/* 六边形雷达标 */}
        <span className="relative flex h-8 w-8 shrink-0 items-center justify-center">
          <span
            className="flex h-6 w-6 items-center justify-center bg-[rgba(0,180,255,0.15)]"
            style={{ clipPath: 'polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%)', border: '1px solid rgba(0,220,255,0.5)' }}
          >
            <i className="dot animate-blink" style={{ background: '#4ff3ff', boxShadow: '0 0 6px #4ff3ff' }} />
          </span>
          <i className="radar-ring" style={{ animationDuration: '6s' }} />
        </span>
        <div>
          <div className="text-base font-bold tracking-widest text-[#e0f6ff]" style={{ textShadow: '0 0 14px rgba(0,220,255,0.5)' }}>{title}</div>
          {sub && <div className="mt-0.5 text-[10px] tracking-[0.25em] text-[#3d6491]">{sub}</div>}
        </div>
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  )
}
