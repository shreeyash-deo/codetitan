import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, ArrowUpRight, CheckCircle2, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ViolationCategoryStat } from '@/services/brandService'

interface IssuesBreakdownChartProps {
  issues?: ViolationCategoryStat[]
}

const CATEGORY_COLORS: Record<string, string> = {
  'Brand Voice': '#3B82F6', // Blue
  'Tone inconsistencies': '#3B82F6',
  'Terminology': '#6366F1', // Indigo
  'Incorrect brand terminology': '#6366F1',
  'Statutory Claims': '#EF4444', // Red
  'Claims & Restrictions': '#EF4444',
  'Unsupported claims': '#EF4444',
  'Visual Identity': '#F59E0B', // Amber
  'Visual inconsistencies': '#F59E0B',
  'General Compliance': '#8B5CF6', // Purple
}

const FALLBACK_COLORS = ['#3B82F6', '#6366F1', '#F59E0B', '#EF4444', '#10B981', '#8B5CF6']

export const IssuesBreakdownChart: React.FC<IssuesBreakdownChartProps> = ({ issues = [] }) => {
  const totalIssues = issues.reduce((acc, curr) => acc + curr.count, 0)

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
              Categorized compliance flags across active copy ({totalIssues} total)
            </CardDescription>
          </div>
          <Link
            to="/content-review"
            className="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-0.5"
          >
            <span>Scan Editor</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-1 pb-5">
        {issues.length === 0 ? (
          <div className="py-8 text-center space-y-3">
            <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">Zero Compliance Violations</p>
              <p className="text-xs text-slate-500 mt-0.5 max-w-xs mx-auto">
                No active violations detected in your workspace content, or no copy has been audited yet.
              </p>
            </div>
            <Link
              to="/content-review"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 transition-colors shadow-2xs"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Audit New Copy</span>
            </Link>
          </div>
        ) : (
          <>
            {/* Proportional Segmented Progress Bar */}
            <div className="space-y-1.5">
              <div className="h-3 w-full rounded-md overflow-hidden flex bg-slate-100 shadow-inner">
                {issues.map((item, idx) => {
                  const color = CATEGORY_COLORS[item.category] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length]
                  return (
                    <div
                      key={item.category}
                      style={{
                        width: `${item.percentage}%`,
                        backgroundColor: color,
                      }}
                      className="h-full transition-all duration-300 hover:opacity-85 relative group cursor-pointer"
                      title={`${item.category}: ${item.count} issues (${item.percentage}%)`}
                    />
                  )
                })}
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Distribution by category</span>
                <span>100% normalized</span>
              </div>
            </div>

            {/* Detailed Category Rows */}
            <div className="space-y-2.5 pt-1">
              {issues.map((item, idx) => {
                const color = CATEGORY_COLORS[item.category] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length]
                return (
                  <div
                    key={item.category}
                    className="p-2.5 rounded-lg border border-border/70 hover:border-slate-300 hover:bg-slate-50/50 transition-all text-xs"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: color }}
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

                    {item.description && (
                      <p className="text-[11px] text-slate-500 leading-tight pl-4">
                        {item.description}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
