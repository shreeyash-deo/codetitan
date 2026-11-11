import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Sparkles,
  AlertTriangle,
  Clock,
  CheckCircle2,
  BookOpen,
  ArrowRight,
  Send,
} from 'lucide-react'

interface EmployeeWorkflowCardProps {
  pendingCount: number
  needsRevisionCount: number
  approvedCount: number
  activeRulesCount: number
}

export const EmployeeWorkflowCard: React.FC<EmployeeWorkflowCardProps> = ({
  pendingCount,
  needsRevisionCount,
  approvedCount,
  activeRulesCount,
}) => {
  const navigate = useNavigate()

  return (
    <Card className="h-full border-border/80 flex flex-col justify-between shadow-xs">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span>Submission Workflow</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Personal status and actions for your content reviews
            </CardDescription>
          </div>
          <Badge
            variant={needsRevisionCount > 0 ? 'warning' : 'neutral'}
            className="text-[10px]"
          >
            {needsRevisionCount > 0 ? `${needsRevisionCount} action items` : 'All caught up'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-4 pb-4 space-y-4">
        {/* If items need revision, show high-priority callout */}
        {needsRevisionCount > 0 ? (
          <div className="p-3.5 rounded-lg bg-amber-50/90 border border-amber-200 text-xs space-y-2">
            <div className="flex items-center gap-2 text-amber-900 font-semibold">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>Revisions Requested</span>
            </div>
            <p className="text-[11px] text-amber-800 leading-relaxed">
              Reviewers have requested edits on {needsRevisionCount} of your submissions. Review comments and resubmit.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/review-history?filter=needs_revision')}
              className="text-xs h-7 text-amber-800 bg-white hover:bg-amber-100/60 border-amber-300 w-full justify-between"
            >
              <span>View & Remediate Copy</span>
              <ArrowRight className="w-3 h-3" />
            </Button>
          </div>
        ) : (
          <div className="p-3.5 rounded-lg bg-emerald-50/70 border border-emerald-200/80 text-xs flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <span className="font-semibold text-slate-800 block">No Revisions Pending</span>
              <span className="text-[11px] text-slate-500">All reviewed submissions have been cleared or approved.</span>
            </div>
          </div>
        )}

        {/* Workflow Counts Breakdown */}
        <div className="grid grid-cols-2 gap-2.5 text-xs">
          <div
            onClick={() => navigate('/review-history?filter=pending')}
            className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 hover:border-blue-200 hover:bg-blue-50/40 transition-colors cursor-pointer group"
          >
            <div className="flex items-center justify-between text-slate-400 group-hover:text-blue-600">
              <span className="text-[10px] uppercase font-semibold">In Review</span>
              <Clock className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl font-bold text-slate-900 mt-1">{pendingCount}</div>
            <span className="text-[10px] text-slate-500">Awaiting sign-off</span>
          </div>

          <div
            onClick={() => navigate('/review-history?filter=approved')}
            className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/40 transition-colors cursor-pointer group"
          >
            <div className="flex items-center justify-between text-slate-400 group-hover:text-emerald-600">
              <span className="text-[10px] uppercase font-semibold">Approved</span>
              <CheckCircle2 className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl font-bold text-slate-900 mt-1">{approvedCount}</div>
            <span className="text-[10px] text-slate-500">Certified to publish</span>
          </div>
        </div>

        {/* Brand Rules Quick Note */}
        <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50/80 border border-slate-100 text-xs">
          <div className="flex items-center gap-2 text-slate-600">
            <BookOpen className="w-3.5 h-3.5 text-blue-600 shrink-0" />
            <span className="text-[11px]">
              <strong>{activeRulesCount}</strong> brand rules active
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/brand-guidelines')}
            className="text-[11px] h-6 px-2 text-blue-600 hover:text-blue-800"
          >
            <span>Browse</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </Button>
        </div>

        {/* Submit Copy Action */}
        <Button
          variant="primaryBlue"
          size="sm"
          onClick={() => navigate('/content-review')}
          className="w-full text-xs font-semibold gap-1.5 shadow-xs"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Review New Content</span>
        </Button>
      </CardContent>
    </Card>
  )
}
