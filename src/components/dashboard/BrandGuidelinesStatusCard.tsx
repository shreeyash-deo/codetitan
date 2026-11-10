import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { BookOpen, CheckCircle, Clock, Database, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

interface BrandGuidelinesStatusCardProps {
  approvedRules?: number
  pendingRules?: number
  sourceDocsCount?: number
  onManageClick?: () => void
}

export const BrandGuidelinesStatusCard: React.FC<BrandGuidelinesStatusCardProps> = ({
  approvedRules = 0,
  pendingRules = 0,
  sourceDocsCount = 0,
  onManageClick,
}) => {
  const totalRules = approvedRules + pendingRules
  const approvalPct = totalRules > 0 ? Math.round((approvedRules / totalRules) * 100) : 100

  return (
    <Card className="h-full border-border/80 flex flex-col justify-between">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-blue-600" />
              <span>Brand Guidelines Status</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Rule engine parameters and vector extraction status
            </CardDescription>
          </div>
          <Badge variant={sourceDocsCount > 0 ? "success" : "neutral"} className="text-[10px] font-medium py-0.5">
            {sourceDocsCount > 0 ? 'Active Memory' : 'No Guidelines'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-1 pb-5">
        {/* Rules Metrics Row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
              <span>Approved Rules</span>
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {approvedRules}
              <span className="text-xs text-slate-400 font-normal"> / {totalRules}</span>
            </div>
            <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-emerald-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${approvalPct}%` }}
              />
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Clock className="w-3.5 h-3.5 text-amber-600" />
              <span>Pending Rules</span>
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {pendingRules}
              <span className="text-xs text-slate-400 font-normal"> candidate{pendingRules === 1 ? '' : 's'}</span>
            </div>
            <p className="text-[10px] text-amber-700 mt-2 font-medium">
              {pendingRules > 0 ? 'Requires Admin sign-off' : 'All candidates reviewed'}
            </p>
          </div>
        </div>

        {/* Knowledge Extraction Status */}
        <div className="p-3 rounded-lg border border-border/80 bg-white space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-xs font-semibold text-slate-800">
                Knowledge Ingestion
              </span>
            </div>
            <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded border ${
              sourceDocsCount > 0
                ? 'text-emerald-700 bg-emerald-50 border-emerald-100'
                : 'text-slate-600 bg-slate-100 border-slate-200'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${sourceDocsCount > 0 ? 'bg-emerald-500' : 'bg-slate-400'}`} />
              {sourceDocsCount > 0 ? 'Indexed & Synced' : 'Awaiting Documents'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
            <div>
              <span className="text-slate-400">Indexed Docs: </span>
              <strong className="text-slate-700">{sourceDocsCount} source{sourceDocsCount === 1 ? '' : 's'}</strong>
            </div>
            <div className="text-right">
              <span className="text-slate-400">Memory Engine: </span>
              <strong className="text-slate-700">BrandShield v2.0</strong>
            </div>
          </div>
        </div>

        <div className="pt-2 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {sourceDocsCount === 0 ? 'Upload PDF or DOCX brand manuals' : `${approvedRules} authoritative rules active`}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onManageClick}
            className="text-xs gap-1.5"
          >
            <span>Manage Guidelines</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
