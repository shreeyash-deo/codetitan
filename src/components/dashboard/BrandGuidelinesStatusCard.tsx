import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { mockGuidelinesTelemetry } from '@/data/mockOverview'
import { BookOpen, CheckCircle, Clock, Database, ArrowRight, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'

interface BrandGuidelinesStatusCardProps {
  onManageClick?: () => void
}

export const BrandGuidelinesStatusCard: React.FC<BrandGuidelinesStatusCardProps> = ({
  onManageClick,
}) => {
  const { approvedRules, pendingRules, totalRules, lastUpdated, knowledgeExtraction } = mockGuidelinesTelemetry

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
          <Badge variant="success" className="text-[10px] font-medium py-0.5">
            Active v2.4
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
                className="bg-emerald-600 h-full rounded-full"
                style={{ width: `${(approvedRules / totalRules) * 100}%` }}
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
              <span className="text-xs text-slate-400 font-normal"> in review</span>
            </div>
            <p className="text-[10px] text-amber-700 mt-2 font-medium">
              Requires brand lead sign-off
            </p>
          </div>
        </div>

        {/* Knowledge Extraction Status */}
        <div className="p-3 rounded-lg border border-border/80 bg-white space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-xs font-semibold text-slate-800">
                Knowledge Extraction
              </span>
            </div>
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              {knowledgeExtraction.status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
            <div>
              <span className="text-slate-400">Indexed Chunks: </span>
              <strong className="text-slate-700">{knowledgeExtraction.indexedChunks}</strong>
            </div>
            <div className="text-right">
              <span className="text-slate-400">Model: </span>
              <strong className="text-slate-700">{knowledgeExtraction.version}</strong>
            </div>
          </div>

          <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1">
            <span>Last rule sync: {lastUpdated}</span>
            <span>Extracted {knowledgeExtraction.lastRun}</span>
          </div>
        </div>

        {/* Action Button */}
        <Link to="/brand-guidelines" className="block w-full">
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs font-medium justify-between hover:bg-slate-50"
            onClick={onManageClick}
          >
            <span>Manage Guidelines & Extraction</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  )
}
