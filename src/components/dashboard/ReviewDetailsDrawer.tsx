import React, { useState } from 'react'
import type { ReviewItem } from '@/types/review'
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
}

export const ReviewDetailsDrawer: React.FC<ReviewDetailsDrawerProps> = ({
  review,
  isOpen,
  onClose,
  onStatusChange,
}) => {
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

      {/* Slide-over panel */}
      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div className="w-screen max-w-xl bg-white shadow-2xl flex flex-col border-l border-border animate-in slide-in-from-right duration-200">
          {/* Header */}
          <div className="p-5 border-b border-border flex items-start justify-between bg-slate-50/70">
            <div className="space-y-1.5 pr-4">
              <div className="flex items-center gap-2 flex-wrap">
                <StatusBadge status={review.status} />
                <Badge variant="outline" className="text-[10px]">
                  {review.contentType}
                </Badge>
                <span className="text-xs text-slate-400 font-mono">
                  ID: {review.id}
                </span>
              </div>
              <h2 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                {review.title}
              </h2>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-slate-400 hover:text-slate-800 hover:bg-slate-200/60 transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            {/* Metadata Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100 text-xs">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-semibold">
                  Submitted By
                </span>
                <div className="flex items-center gap-1.5 mt-1">
                  <Avatar className="w-4 h-4">
                    <AvatarImage src={review.author.avatar} />
                    <AvatarFallback>{review.author.name.substring(0, 2)}</AvatarFallback>
                  </Avatar>
                  <span className="font-medium text-slate-800 truncate">
                    {review.author.name}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 uppercase font-semibold">
                  Date
                </span>
                <div className="font-medium text-slate-800 mt-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-400" />
                  {review.date}
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 uppercase font-semibold">
                  Compliance Score
                </span>
                <div className="text-base font-extrabold text-slate-900 mt-0.5">
                  {review.score}
                  <span className="text-xs text-slate-400 font-normal">/100</span>
                </div>
              </div>
            </div>

            {/* AI Summary Banner */}
            <div className="p-3.5 rounded-lg bg-blue-50/60 border border-blue-100 text-xs text-slate-700 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-blue-900">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>AI Governance Assessment</span>
              </div>
              <p className="leading-relaxed">{review.summary}</p>
            </div>

            {/* Content Preview */}
            {review.contentPreview && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                  Content Excerpt
                </h4>
                <div className="p-3 rounded-md bg-slate-50 border border-slate-200 text-xs font-serif text-slate-700 leading-relaxed italic">
                  "{review.contentPreview}"
                </div>
              </div>
            )}

            {/* Detected Issues List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  Detected Issues ({review.issues?.length || 0})
                </h4>
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
          </div>
        </div>
      </div>
    </div>
  )
}
