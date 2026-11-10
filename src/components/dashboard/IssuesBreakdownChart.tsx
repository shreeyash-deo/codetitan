import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { mockIssuesBreakdown } from '@/data/mockOverview'
import { AlertTriangle, Info, ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export const IssuesBreakdownChart: React.FC = () => {
  const totalIssues = mockIssuesBreakdown.reduce((acc, curr) => acc + curr.count, 0)

  return (
    <Card className="h-full border-border/80 flex flex-col justify-between">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <span>Issues Breakdown</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Categorized compliance flags detected across last 30 days ({totalIssues} total)
            </CardDescription>
          </div>
          <Link
            to="/content-review"
            className="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-0.5"
          >
            <span>Resolve</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-1 pb-5">
        {/* Proportional Segmented Progress Bar */}
        <div className="space-y-1.5">
          <div className="h-3 w-full rounded-md overflow-hidden flex bg-slate-100 shadow-inner">
            {mockIssuesBreakdown.map((item) => (
              <div
                key={item.category}
                style={{
                  width: `${item.percentage}%`,
                  backgroundColor: item.color,
                }}
                className="h-full transition-all duration-300 hover:opacity-85 relative group cursor-pointer"
                title={`${item.category}: ${item.count} issues (${item.percentage}%)`}
              />
            ))}
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Aggregated distribution</span>
            <span>100% normalized</span>
          </div>
        </div>

        {/* Detailed Category Rows */}
        <div className="space-y-2.5 pt-1">
          {mockIssuesBreakdown.map((item) => (
            <div
              key={item.category}
              className="p-2.5 rounded-lg border border-border/70 hover:border-slate-300 hover:bg-slate-50/50 transition-all text-xs"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="font-semibold text-slate-800 truncate">
                    {item.category}
                  </span>
                  <Badge
                    variant={
                      item.severity === 'critical'
                        ? 'destructive'
                        : item.severity === 'moderate'
                        ? 'warning'
                        : 'secondary'
                    }
                    className="text-[9px] uppercase px-1.5 py-0"
                  >
                    {item.severity}
                  </Badge>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="font-bold text-slate-900">{item.count}</span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    ({item.percentage}%)
                  </span>
                </div>
              </div>

              <p className="text-[11px] text-slate-500 leading-tight pl-4">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
