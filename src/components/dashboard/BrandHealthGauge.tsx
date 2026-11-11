import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ShieldCheck, TrendingUp, CheckCircle2, AlertCircle } from 'lucide-react'

interface BrandHealthGaugeProps {
  score: number
  total?: number
  hasReviews?: boolean
  trend?: string
  orgName?: string
  activeRulesCount?: number
  isEmployee?: boolean
}

export const BrandHealthGauge: React.FC<BrandHealthGaugeProps> = ({
  score = 100,
  total = 100,
  hasReviews = false,
  trend = '+4.2 pts',
  orgName = 'Organisation',
  activeRulesCount = 0,
  isEmployee = false,
}) => {
  // Calculate SVG arc parameters for a clean semi-circle gauge
  const radius = 70
  const circumference = Math.PI * radius
  const displayScore = hasReviews ? score : 0
  const strokeDashoffset = circumference - (displayScore / total) * circumference

  const subCategories = [
    { name: 'Voice & Tone', score: hasReviews ? Math.min(100, Math.max(60, score + 4)) : 0, target: 85 },
    { name: 'Brand Terminology', score: hasReviews ? Math.min(100, Math.max(60, score - 2)) : 0, target: 85 },
    { name: 'Visual & Identity', score: hasReviews ? Math.min(100, Math.max(60, score + 1)) : 0, target: 85 },
    { name: 'Statutory Claims', score: hasReviews ? Math.min(100, Math.max(60, score - 8)) : 0, target: 85 },
  ]

  const healthVariant = !hasReviews
    ? 'neutral'
    : score >= 85
    ? 'blue'
    : score >= 70
    ? 'warning'
    : 'destructive'

  const healthLabel = !hasReviews
    ? 'Awaiting Audits'
    : score >= 85
    ? 'Health: Strong'
    : score >= 70
    ? 'Health: Moderate'
    : 'Health: Needs Attention'

  return (
    <Card className="h-full border-border/80 flex flex-col justify-between">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <span>{isEmployee ? 'My Content Health Index' : 'Brand Health Index'}</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              {isEmployee
                ? 'Compliance posture across your submitted copy'
                : `Aggregated governance posture across all ${orgName} touchpoints`}
            </CardDescription>
          </div>
          <Badge variant={healthVariant as any} className="text-[11px] font-medium py-0.5">
            {healthLabel}
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
                stroke={hasReviews ? (score >= 85 ? '#2563EB' : score >= 70 ? '#F59E0B' : '#EF4444') : '#94A3B8'}
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
                {hasReviews ? score : '--'}
                {hasReviews && <span className="text-sm font-semibold text-slate-400">/{total}</span>}
              </div>
              <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                Overall Index
              </span>
            </div>
          </div>

          {/* Benchmark Comparison & Status */}
          <div className="space-y-2 text-left sm:border-l sm:border-border sm:pl-6">
            {hasReviews ? (
              <>
                <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-medium">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span>{trend} vs 30-day baseline</span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed max-w-[210px]">
                  {isEmployee
                    ? 'Your submitted copy is actively evaluated against approved brand rules.'
                    : `${orgName} content compliance is actively monitored against approved brand memory.`}
                </p>
              </>
            ) : (
              <>
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                  <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
                  <span>Baseline pending</span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed max-w-[210px]">
                  {isEmployee
                    ? 'No copy submitted yet. Review an asset to calculate your initial score.'
                    : 'No marketing copy has been scanned yet. Review an asset to calculate your initial health index.'}
                </p>
              </>
            )}
            <div className="flex items-center gap-2 pt-1">
              <span className="inline-flex items-center gap-1 text-[11px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                {activeRulesCount} rules active
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
                  {hasReviews ? `${cat.score}%` : '--'}
                </span>
                <span className={`text-[10px] font-medium ${
                  !hasReviews ? 'text-slate-400' : cat.score >= cat.target ? 'text-emerald-600' : 'text-amber-600'
                }`}>
                  {!hasReviews ? 'Pending' : cat.score >= cat.target ? 'Optimal' : 'Review'}
                </span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    !hasReviews ? 'bg-slate-300' : cat.score >= cat.target ? 'bg-blue-600' : 'bg-amber-500'
                  }`}
                  style={{ width: `${hasReviews ? cat.score : 0}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
