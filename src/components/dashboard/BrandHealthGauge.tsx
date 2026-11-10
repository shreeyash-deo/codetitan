import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ShieldCheck, TrendingUp, CheckCircle2, AlertCircle } from 'lucide-react'

interface BrandHealthGaugeProps {
  score: number // e.g. 87
  total?: number // 100
  trend?: string // "+4.2 pts"
}

export const BrandHealthGauge: React.FC<BrandHealthGaugeProps> = ({
  score = 87,
  total = 100,
  trend = '+4.2 pts',
}) => {
  // Calculate SVG arc parameters for a clean semi-circle gauge
  const radius = 70
  const circumference = Math.PI * radius
  const strokeDashoffset = circumference - (score / total) * circumference

  const subCategories = [
    { name: 'Voice & Tone', score: 92, target: 90, status: 'optimal' },
    { name: 'Brand Terminology', score: 88, target: 85, status: 'optimal' },
    { name: 'Visual & Identity', score: 90, target: 85, status: 'optimal' },
    { name: 'Statutory Claims', score: 78, target: 85, status: 'attention' },
  ]

  return (
    <Card className="h-full border-border/80 flex flex-col justify-between">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <span>Brand Health Index</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Aggregated governance posture across all NovaPay touchpoints
            </CardDescription>
          </div>
          <Badge variant="blue" className="text-[11px] font-medium py-0.5">
            Health: Strong
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-2 pb-5 space-y-6">
        {/* Large Score Visualizer */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-8 pt-2">
          {/* Gauge Arc */}
          <div className="relative flex flex-col items-center justify-center">
            <svg
              className="w-44 h-28 overflow-visible"
              viewBox="0 0 160 90"
            >
              {/* Background Arc */}
              <path
                d="M 10 80 A 70 70 0 0 1 150 80"
                fill="none"
                stroke="#E2E8F0"
                strokeWidth="12"
                strokeLinecap="round"
              />
              {/* Active Foreground Arc */}
              <path
                d="M 10 80 A 70 70 0 0 1 150 80"
                fill="none"
                stroke="#2563EB"
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-1000 ease-out"
              />
            </svg>

            {/* Score Text in Center of Arc */}
            <div className="absolute bottom-1 text-center">
              <div className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
                {score}
                <span className="text-sm font-semibold text-slate-400">/{total}</span>
              </div>
              <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                Overall Index
              </span>
            </div>
          </div>

          {/* Quick Benchmark Comparison */}
          <div className="space-y-2 text-left sm:border-l sm:border-border sm:pl-6">
            <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-medium">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>{trend} vs 30-day baseline</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed max-w-[210px]">
              NovaPay is currently tracking <strong className="text-slate-800">7.2% above</strong> average fintech industry compliance standards.
            </p>
            <div className="flex items-center gap-2 pt-1">
              <span className="inline-flex items-center gap-1 text-[11px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                121 rules active
              </span>
            </div>
          </div>
        </div>

        {/* Breakdown by Pillars */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-3 border-t border-border/60">
          {subCategories.map((cat) => (
            <div
              key={cat.name}
              className="p-2.5 rounded-md bg-slate-50/70 border border-slate-100 space-y-1"
            >
              <div className="text-[11px] font-medium text-slate-600 truncate">
                {cat.name}
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-base font-bold text-slate-900">
                  {cat.score}%
                </span>
                <span className={`text-[10px] font-medium ${
                  cat.score >= cat.target ? 'text-emerald-600' : 'text-amber-600'
                }`}>
                  {cat.score >= cat.target ? 'Optimal' : 'Review'}
                </span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    cat.score >= cat.target ? 'bg-blue-600' : 'bg-amber-500'
                  }`}
                  style={{ width: `${cat.score}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
