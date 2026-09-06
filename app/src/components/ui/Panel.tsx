import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** HUD 科技风面板容器 */
export default function Panel({
  title,
  sub,
  right,
  className,
  bodyClassName,
  children,
}: {
  title?: string
  sub?: string
  right?: ReactNode
  className?: string
  bodyClassName?: string
  children: ReactNode
}) {
  return (
    <div className={cn('tech-panel flex min-h-0 flex-col', className)}>
      {title && (
        <div className="flex items-center justify-between border-b border-[rgba(0,200,255,0.14)] px-3 py-2">
          <div className="flex items-baseline gap-2">
            <div className="panel-title">{title}</div>
            {sub && <span className="text-[9px] tracking-[0.2em] text-[#3d6491]">{sub}</span>}
          </div>
          {right}
        </div>
      )}
      <div className={cn('min-h-0 flex-1 px-3 py-2', bodyClassName)}>{children}</div>
    </div>
  )
}
