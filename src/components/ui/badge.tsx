import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 select-none tracking-tight',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-slate-900 text-white shadow-xs',
        secondary:
          'border-slate-200 bg-slate-100 text-slate-700',
        outline:
          'border-slate-300 text-slate-700 bg-white',
        blue:
          'border-blue-200 bg-blue-50 text-blue-700',
        success:
          'border-emerald-200 bg-emerald-50 text-emerald-700 font-medium',
        warning:
          'border-amber-200 bg-amber-50 text-amber-700 font-medium',
        destructive:
          'border-rose-200 bg-rose-50 text-rose-700 font-medium',
        neutral:
          'border-slate-200 bg-white text-slate-600',
      },
      size: {
        default: 'px-2 py-0.5 text-[11px]',
        sm: 'px-1.5 py-0.2 text-[10px] leading-tight',
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
