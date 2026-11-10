import React, { useState } from 'react'
import type { HistoricalReviewRecord } from '@/types/approval'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { ApprovalTimelineWidget } from './ApprovalTimelineWidget'
import {
  X,
  FileCheck2,
  Calendar,
  User,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  GitCompare,
  MessageSquare,
  Sparkles,
  Send,
  CornerDownRight,
} from 'lucide-react'

interface ReviewDetailReportModalProps {
  review: HistoricalReviewRecord | null
  isOpen: boolean
  onClose: () => void
  onAddComment?: (reviewId: string, commentText: string) => void
}

export const ReviewDetailReportModal: React.FC<ReviewDetailReportModalProps> = ({
  review,
  isOpen,
  onClose,
  onAddComment,
}) => {
  const [activeTab, setActiveTab] = useState<'diff' | 'findings' | 'timeline' | 'comments'>('diff')
  const [commentInput, setCommentInput] = useState('')

  if (!isOpen || !review) return null

  const handleSendComment = (e: React.FormEvent) => {
    e.preventDefault()
    if (!commentInput.trim()) return
    onAddComment?.(review.id, commentInput.trim())
    setCommentInput('')
  }

  const getStatusBadge = (status: HistoricalReviewRecord['approvalStatus']) => {
    switch (status) {
      case 'approved':
        return <Badge variant="success">Approved</Badge>
      case 'pending':
        return <Badge variant="blue">Pending Approval</Badge>
      case 'needs_revision':
        return <Badge variant="warning">Needs Revision</Badge>
      case 'critical_issues':
        return <Badge variant="destructive">Critical Issues</Badge>
      default:
        return null
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-3 sm:p-4">
        <div className="relative w-full max-w-4xl rounded-xl bg-white shadow-2xl border border-border p-5 sm:p-6 space-y-5 animate-in zoom-in-95 duration-150 max-h-[92vh] flex flex-col">
          {/* Header */}
          <div className="flex items-start justify-between pb-4 border-b border-border gap-4 shrink-0">
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                {getStatusBadge(review.approvalStatus)}
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
              className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs shrink-0">
            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Author</span>
              <div className="flex items-center gap-1.5 mt-1 font-medium text-slate-800 truncate">
                <Avatar className="w-4 h-4">
                  <AvatarImage src={review.submittedBy.avatar} />
                  <AvatarFallback>{review.submittedBy.name.substring(0, 2)}</AvatarFallback>
                </Avatar>
                <span className="truncate">{review.submittedBy.name}</span>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Reviewer</span>
              <div className="flex items-center gap-1.5 mt-1 font-medium text-slate-800 truncate">
                <Avatar className="w-4 h-4">
                  <AvatarImage src={review.assignedReviewer.avatar} />
                  <AvatarFallback>{review.assignedReviewer.name.substring(0, 2)}</AvatarFallback>
                </Avatar>
                <span className="truncate">{review.assignedReviewer.name}</span>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Compliance Index</span>
              <div className="text-sm font-bold text-slate-900 mt-0.5">
                {review.score}/100
                <span className="text-[10px] text-slate-400 font-normal ml-1">
                  ({review.violationsCount} violations)
                </span>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Corrections</span>
              <div className="text-xs font-semibold text-slate-700 mt-0.5">
                <span className="text-emerald-700">{review.acceptedSuggestionsCount} Accepted</span>
                <span className="text-slate-300 mx-1">•</span>
                <span className="text-slate-500">{review.rejectedSuggestionsCount} Rejected</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1 border-b border-border pb-1 shrink-0 text-xs font-medium">
            <button
              onClick={() => setActiveTab('diff')}
              className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
                activeTab === 'diff'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <GitCompare className="w-3.5 h-3.5" />
              <span>Version Diff</span>
            </button>

            <button
              onClick={() => setActiveTab('findings')}
              className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
                activeTab === 'findings'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI Findings ({review.findings.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('timeline')}
              className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
                activeTab === 'timeline'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Approval Timeline ({review.timeline.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('comments')}
              className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
                activeTab === 'comments'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Reviewer Comments ({review.comments.length})</span>
            </button>
          </div>

          {/* Tab 1: Version Diff */}
          {activeTab === 'diff' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 overflow-y-auto flex-1">
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-rose-700 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  Original Content Submitted
                </span>
                <div className="p-3.5 rounded-lg bg-rose-50/40 border border-rose-200 text-xs font-serif leading-relaxed text-slate-800 min-h-[220px] whitespace-pre-wrap">
                  {review.originalContent}
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Corrected Content (Active)
                </span>
                <div className="p-3.5 rounded-lg bg-emerald-50/40 border border-emerald-200 text-xs font-serif leading-relaxed text-slate-800 min-h-[220px] whitespace-pre-wrap">
                  {review.correctedContent}
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: AI Findings */}
          {activeTab === 'findings' && (
            <div className="space-y-3 overflow-y-auto flex-1">
              {review.findings.length === 0 ? (
                <div className="p-8 text-center text-xs text-emerald-800 bg-emerald-50/50 rounded-lg border border-emerald-200">
                  <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto mb-1" />
                  <p className="font-semibold">Zero Outstanding Policy Violations</p>
                  <p className="text-[11px] text-emerald-700 mt-0.5">Asset conforms to all active BrandShield rules.</p>
                </div>
              ) : (
                review.findings.map((f) => (
                  <div
                    key={f.id}
                    className="p-3 rounded-lg border border-border bg-white text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={f.severity === 'critical' ? 'destructive' : 'warning'}
                          className="text-[9px] uppercase"
                        >
                          {f.severity}
                        </Badge>
                        <span className="font-semibold text-slate-900">{f.category}</span>
                      </div>
                    </div>

                    <div className="p-2 rounded bg-rose-50/80 border border-rose-200 text-rose-950 font-mono text-[11px]">
                      <span className="text-rose-500 font-bold mr-1">✕</span>
                      "{f.snippet}"
                    </div>

                    <p className="text-slate-600 text-[11px] leading-snug">{f.explanation}</p>

                    <div className="p-2 rounded bg-blue-50/70 border border-blue-200 text-blue-950 text-[11px] flex items-start gap-1.5">
                      <CornerDownRight className="w-3.5 h-3.5 text-blue-600 mt-0.5 shrink-0" />
                      <span>{f.suggestion}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 3: Approval Timeline */}
          {activeTab === 'timeline' && (
            <div className="overflow-y-auto flex-1 p-2">
              <ApprovalTimelineWidget timeline={review.timeline} />
            </div>
          )}

          {/* Tab 4: Reviewer Comments */}
          {activeTab === 'comments' && (
            <div className="space-y-4 overflow-y-auto flex-1 flex flex-col justify-between">
              <div className="space-y-3">
                {review.comments.map((c) => (
                  <div
                    key={c.id}
                    className="p-3 rounded-lg border border-border bg-slate-50/60 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Avatar className="w-5 h-5">
                          <AvatarImage src={c.authorAvatar} />
                          <AvatarFallback>{c.authorName.substring(0, 2)}</AvatarFallback>
                        </Avatar>
                        <span className="font-semibold text-slate-900">{c.authorName}</span>
                        <span className="text-[10px] text-slate-400">({c.authorRole})</span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">{c.timestamp}</span>
                    </div>
                    <p className="text-slate-700 leading-relaxed pl-7">{c.text}</p>
                  </div>
                ))}
              </div>

              {/* Add comment input */}
              <form onSubmit={handleSendComment} className="flex items-center gap-2 pt-2 border-t border-border">
                <input
                  type="text"
                  placeholder="Add a governance comment or revision note..."
                  value={commentInput}
                  onChange={(e) => setCommentInput(e.target.value)}
                  className="flex-1 h-8 rounded-md border border-input bg-white px-3 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500"
                />
                <Button type="submit" variant="primaryBlue" size="sm" className="h-8 gap-1">
                  <Send className="w-3 h-3" />
                  <span>Send</span>
                </Button>
              </form>
            </div>
          )}

          {/* Footer */}
          <div className="pt-3 border-t border-border flex items-center justify-between shrink-0">
            <span className="text-[11px] text-slate-400">
              Evaluated under NovaPay Brand Governance Policies v2.4
            </span>
            <Button variant="outline" size="sm" onClick={onClose}>
              Close Report
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
