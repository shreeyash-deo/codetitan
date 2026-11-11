import React, { useState } from 'react'
import type { ReviewItem } from '@/types/review'
import { useWorkspace } from '@/hooks/useWorkspace'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  X,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  Calendar,
  Share2,
  ExternalLink,
  Check,
} from 'lucide-react'

interface ReviewDetailsDrawerProps {
  review: ReviewItem | null
  isOpen: boolean
  onClose: () => void
  onStatusChange?: (reviewId: string, newStatus: ReviewItem['status']) => void
  userRole?: string
}

export const ReviewDetailsDrawer: React.FC<ReviewDetailsDrawerProps> = ({
  review,
  isOpen,
  onClose,
  onStatusChange,
  userRole: propUserRole,
}) => {
  const { currentWorkspace } = useWorkspace()
  const effectiveRole = (propUserRole ?? currentWorkspace?.role ?? '').trim().toLowerCase()
  const isReviewerOrAdmin = ['admin', 'reviewer'].includes(effectiveRole)

  const [appliedIssues, setAppliedIssues] = useState<Record<string, boolean>>({})

  if (!isOpen || !review) return null

  const toggleApplyFix = (issueId: string) => {
    setAppliedIssues(prev => ({
      ...prev,
      [issueId]: !prev[issueId],
    }))
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs transition-opacity duration-200"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-xl bg-white shadow-2xl border-l border-border flex flex-col">
          {/* Header */}
          <div className="p-5 border-b border-border bg-slate-50/50 flex items-start justify-between gap-4">
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  {review.channel} • {review.contentType}
                </span>
                <StatusBadge status={review.status} />
              </div>
              <h2 className="text-lg font-bold text-slate-900 truncate">
                {review.title}
              </h2>
              <div className="flex items-center gap-2 text-xs text-slate-500 pt-0.5">
                <Avatar className="w-4 h-4">
                  {review.author.avatar && <AvatarImage src={review.author.avatar} />}
                  <AvatarFallback className="text-[8px]">
                    {review.author.name.charAt(0)}
                  </AvatarFallback>
                </Avatar>
                <span>{review.author.name}</span>
                <span>•</span>
                <span>{review.submittedAt || review.date}</span>
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-slate-400 hover:text-slate-600 rounded-lg shrink-0"
              onClick={onClose}
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            {/* Score & Summary Banner */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-blue-50/60 to-indigo-50/40 border border-blue-100 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-blue-900 uppercase tracking-wider">
                  Compliance Posture
                </span>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className={`text-3xl font-extrabold ${
                    review.score >= 85
                      ? 'text-emerald-600'
                      : review.score >= 70
                      ? 'text-amber-600'
                      : 'text-rose-600'
                  }`}>
                    {review.score}
                  </span>
                  <span className="text-xs text-slate-500">/ 100</span>
                </div>
              </div>

              <div className="text-right">
                <span className="text-xs font-medium text-slate-500 block">
                  Violations Found
                </span>
                <Badge
                  variant={review.issuesDetected > 0 ? 'destructive' : 'neutral'}
                  className="mt-1"
                >
                  {review.issuesDetected} {review.issuesDetected === 1 ? 'Rule' : 'Rules'} Triggered
                </Badge>
              </div>
            </div>

            {/* Content Preview */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>Audited Content Snippet</span>
              </span>
              <div className="p-3.5 rounded-lg border border-border bg-slate-50/60 text-xs text-slate-700 leading-relaxed font-sans max-h-48 overflow-y-auto">
                {review.contentPreview || review.summary || 'No content preview available.'}
              </div>
            </div>

            {/* Findings & Suggestions */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  <span>Rule Engine Findings ({review.issues?.length || 0})</span>
                </span>
                {review.issues && review.issues.length > 0 && (
                  <span className="text-[11px] text-slate-400">
                    Click "Apply Fix" to adopt suggestions
                  </span>
                )}
              </div>

              {(!review.issues || review.issues.length === 0) ? (
                <div className="p-4 rounded-lg bg-emerald-50/50 border border-emerald-100 text-center text-xs text-emerald-800 space-y-1">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 mx-auto" />
                  <p className="font-semibold">Zero Compliance Violations Found</p>
                  <p className="text-[11px] text-emerald-700">
                    This asset satisfies all active voice, tone, and statutory brand rules.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {review.issues.map((issue) => {
                    const isApplied = appliedIssues[issue.id]
                    return (
                      <div
                        key={issue.id}
                        className={`p-3.5 rounded-lg border transition-all text-xs space-y-2.5 ${
                          isApplied
                            ? 'bg-emerald-50/40 border-emerald-200'
                            : 'bg-white border-border/80 shadow-xs'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-900">
                              {issue.category}
                            </span>
                            <Badge
                              variant={
                                issue.severity === 'critical'
                                  ? 'destructive'
                                  : 'warning'
                              }
                              className="text-[9px] uppercase px-1.5 py-0"
                            >
                              {issue.severity}
                            </Badge>
                          </div>

                          <Button
                            variant={isApplied ? 'outline' : 'primaryBlue'}
                            size="sm"
                            className="h-7 text-[11px] gap-1"
                            onClick={() => toggleApplyFix(issue.id)}
                          >
                            {isApplied ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-600" />
                                <span>Applied</span>
                              </>
                            ) : (
                              <>
                                <Sparkles className="w-3 h-3" />
                                <span>Apply Fix</span>
                              </>
                            )}
                          </Button>
                        </div>

                        {/* Flagged snippet */}
                        <div className="p-2 rounded bg-rose-50/70 border border-rose-200 text-rose-900 font-mono text-[11px]">
                          <span className="text-rose-500 font-bold mr-1">✕</span>
                          "{issue.snippet}"
                        </div>

                        {/* Explanation */}
                        <p className="text-slate-600 leading-snug">
                          {issue.explanation}
                        </p>

                        {/* Suggestion */}
                        <div className="p-2 rounded bg-blue-50/60 border border-blue-200 text-blue-950 text-[11px]">
                          <span className="font-semibold text-blue-700">Suggested Correction: </span>
                          {issue.suggestion}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-border bg-slate-50 flex items-center justify-between gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
            >
              Close
            </Button>

            {isReviewerOrAdmin && (
              <div className="flex items-center gap-2">
                {review.status !== 'rejected' && (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => {
                      onStatusChange?.(review.id, 'rejected')
                      onClose()
                    }}
                  >
                    Reject Asset
                  </Button>
                )}

                {review.status !== 'approved' && (
                  <Button
                    variant="primaryBlue"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => {
                      onStatusChange?.(review.id, 'approved')
                      onClose()
                    }}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Approve Content</span>
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
