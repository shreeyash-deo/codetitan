import React from 'react'
import { cn } from '@/lib/utils'

interface BrandShieldLogoProps {
  collapsed?: boolean
  className?: string
}

export const BrandShieldLogo: React.FC<BrandShieldLogoProps> = ({
  collapsed = false,
  className,
}) => {
  return (
    <div className={cn('flex items-center gap-2.5 select-none', className)}>
      <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-b from-blue-500 to-blue-700 text-white shadow-sm ring-1 ring-white/10 shrink-0">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-4 h-4 text-white"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
        <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-400"></span>
        </span>
      </div>

      {!collapsed && (
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold tracking-tight text-white">
              Brand<span className="text-blue-400 font-bold">Shield</span>
            </span>
            <span className="text-[10px] font-mono px-1 py-0.5 rounded bg-blue-500/15 text-blue-300 font-medium border border-blue-500/20">
              v1.0
            </span>
          </div>
          <span className="text-[10px] text-slate-400 tracking-tight truncate">
            Enterprise Governance
          </span>
        </div>
      )}
    </div>
  )
}
