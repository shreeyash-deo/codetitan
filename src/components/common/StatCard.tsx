import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowUpRight, ArrowDownRight, type LucideIcon, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  change?: string
  isPositive?: boolean
  trendDescription?: string
  icon?: LucideIcon
  className?: string
  onClick?: () => void
  highlight?: boolean
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  change,
  isPositive = true,
  trendDescription,
  icon: Icon,
  className,
  onClick,
  highlight = false,
}) => {
  return (
    <Card
      onClick={onClick}
      className={cn(
        'overflow-hidden relative border-border/80 transition-all select-none',
        onClick && 'cursor-pointer hover:border-slate-300 hover:shadow-sm active:scale-[0.99] group',
        highlight && 'bg-blue-50/20 border-blue-200/90 shadow-xs',
        className
      )}
    >
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider truncate">
            {label}
          </p>
          <div className="flex items-center gap-1">
            {Icon && (
              <div className="p-1 rounded bg-slate-50 border border-slate-100 text-slate-500">
                <Icon className="w-3.5 h-3.5" />
              </div>
            )}
            {onClick && (
              <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-600 group-hover:translate-x-0.5 transition-all" />
            )}
          </div>
        </div>

        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            {value}
          </span>
        </div>

        {(change || trendDescription) && (
          <div className="mt-2.5 flex items-center gap-1.5 text-xs text-slate-500 flex-wrap">
            {change && (
              <span
                className={cn(
                  'inline-flex items-center font-medium text-[11px] px-1.5 py-0.2 rounded shrink-0',
                  isPositive
                    ? 'text-emerald-700 bg-emerald-50'
                    : 'text-amber-700 bg-amber-50'
                )}
              >
                {isPositive ? (
                  <ArrowUpRight className="w-3 h-3 mr-0.5 inline" />
                ) : (
                  <ArrowDownRight className="w-3 h-3 mr-0.5 inline" />
                )}
                {change}
              </span>
            )}
            {trendDescription && (
              <span className="text-slate-400 text-[11px] truncate">
                {trendDescription}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
