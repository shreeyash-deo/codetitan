import React, { useState, useEffect } from 'react'
import type { HistoricalReviewRecord } from '@/types/approval'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { ApprovalTimelineWidget } from './ApprovalTimelineWidget'
import { VersionHistoryModal } from '@/components/studio/VersionHistoryModal'
import { CompareDiffModal } from '@/components/studio/CompareDiffModal'
import { reviewService } from '@/services/reviewService'
import type { ContentVersionSummary } from '@/types/version'
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
  History,
  Layers,
  Lock,
  RefreshCw,
  ArrowRight,
  Clock,
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
  const [activeTab, setActiveTab] = useState<'history' | 'diff' | 'findings' | 'timeline' | 'comments'>('history')
  const [commentInput, setCommentInput] = useState('')
  const [isVersionHistoryModalOpen, setIsVersionHistoryModalOpen] = useState(false)
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false)
  const [versionsList, setVersionsList] = useState<ContentVersionSummary[]>([])
  const [isLoadingVersions, setIsLoadingVersions] = useState(false)

  const reviewNumericId = review?.id ? String(review.id).replace(/\D/g, '') || review.id : null

  useEffect(() => {
    if (!isOpen || !reviewNumericId) return
    const fetchVersions = async () => {
      setIsLoadingVersions(true)
      try {
        const list = await reviewService.getVersions(reviewNumericId)
        if (list) {
          setVersionsList(list)
        }
      } catch (err) {
        console.error('Failed to load version history for review:', err)
      } finally {
        setIsLoadingVersions(false)
      }
    }
    fetchVersions()
  }, [isOpen, reviewNumericId])

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
                <Button
                  variant="outline"
                  size="sm"
                  className="h-6 text-[11px] gap-1 text-blue-700 border-blue-200 hover:bg-blue-50"
                  onClick={() => setIsVersionHistoryModalOpen(true)}
                >
                  <History className="w-3 h-3 text-blue-600" />
                  <span>Version History ({versionsList.length})</span>
                </Button>
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
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Author</span>
              <div className="flex items-center gap-1.5 mt-1 font-medium text-slate-800 truncate">
                <Avatar className="w-4 h-4">
                  <AvatarImage src={review?.submittedBy?.avatar} />
                  <AvatarFallback>{review?.submittedBy?.name ? review.submittedBy.name.slice(0, 2) : 'AU'}</AvatarFallback>
                </Avatar>
                <span className="truncate">{review?.submittedBy?.name || 'Author'}</span>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Reviewer</span>
              <div className="flex items-center gap-1.5 mt-1 font-medium text-slate-800 truncate">
                <Avatar className="w-4 h-4">
                  <AvatarImage src={review?.assignedReviewer?.avatar} />
                  <AvatarFallback>{review?.assignedReviewer?.name ? review.assignedReviewer.name.slice(0, 2) : 'RV'}</AvatarFallback>
                </Avatar>
                <span className="truncate">{review?.assignedReviewer?.name || 'Reviewer'}</span>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Compliance Index</span>
              <div className="flex items-center gap-1.5 text-sm font-bold text-slate-900 mt-0.5">
                <span>{review.score}/100</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  (review.auditStatus || 'verified') === 'verified'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : (review.auditStatus === 'failed' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-amber-50 text-amber-700 border border-amber-200')
                }`}>
                  {(review.auditStatus || 'verified') === 'verified' ? 'Verified' : review.auditStatus}
                </span>
                <span className="text-[10px] text-slate-400 font-normal ml-0.5">
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
          <div className="flex items-center gap-1 border-b border-border pb-1 shrink-0 text-xs font-medium flex-wrap">
            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
                activeTab === 'history'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Version History ({versionsList.length})</span>
            </button>

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

          {/* Tab 0: Version History */}
          {activeTab === 'history' && (
            <div className="space-y-3 overflow-y-auto flex-1">
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-blue-600" />
                  <span className="font-semibold text-slate-800 text-xs">
                    Immutable Historical Versions ({versionsList.length})
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs gap-1 text-blue-700 border-blue-200"
                  onClick={() => setIsVersionHistoryModalOpen(true)}
                >
                  <Layers className="w-3.5 h-3.5 text-blue-600" />
                  <span>Interactive Version Inspector</span>
                </Button>
              </div>

              {isLoadingVersions ? (
                <div className="flex items-center justify-center p-8 text-slate-400 gap-2 text-xs">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                  <span>Loading version records...</span>
                </div>
              ) : versionsList.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs border border-dashed rounded-lg bg-slate-50/50">
                  No version snapshots found for this review.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {versionsList.map((v) => (
                    <div
                      key={v.id}
                      className="p-3.5 rounded-lg border border-slate-200 bg-white hover:border-slate-300 shadow-2xs space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 font-mono">
                            v{v.versionNumber}
                          </span>
                          <span className="font-semibold text-slate-800">
                            {v.changeDescription || (v.versionNumber === 1 ? 'Initial Submission' : 'Content updated')}
                          </span>
                          {v.isCurrent && (
                            <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200 font-semibold">
                              Current Active
                            </Badge>
                          )}
                          {v.versionNumber === 1 && (
                            <Badge variant="outline" className="text-[10px] text-slate-600 border-slate-300">
                              Original
                            </Badge>
                          )}
                        </div>

                        <div className="flex items-center gap-1.5">
                          {v.versionState === 'approved' ? (
                            <Badge variant="success" className="text-[10px]">Approved</Badge>
                          ) : v.versionState === 'submitted' ? (
                            <Badge variant="blue" className="text-[10px]">Submitted for Sign-off</Badge>
                          ) : v.versionState === 'changes_requested' ? (
                            <Badge variant="warning" className="text-[10px]">Changes Requested</Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px]">{v.versionState || 'Audited'}</Badge>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3 text-slate-400" />
                            {new Date(v.createdAt).toLocaleString()}
                          </span>
                          {v.authorName && (
                            <span className="flex items-center gap-1 text-slate-700 font-medium">
                              <User className="w-3 h-3 text-slate-400" />
                              {v.authorName}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2.5">
                          <span className="font-semibold">
                            Score: <strong className={(v.complianceScore ?? (v as any).compliance_score ?? 100) >= 90 ? 'text-emerald-700' : 'text-blue-700'}>{v.complianceScore ?? (v as any).compliance_score ?? 100}/100</strong>
                          </span>
                          <span className="text-slate-400 font-mono">
                            {v.findingsCount ?? (v as any).findings_count ?? 0} violations
                          </span>
                          <span className="text-[10px] font-mono text-slate-400">
                            SHA: {(v.contentHash || (v as any).content_hash || '').slice(0, 8)}...
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

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
                review.findings.map((f: any) => {
                  const offendingText = (f.originalText || f.snippet || '').trim()
                  const suggestedAlternative = (f.suggestedCorrection || f.suggestion || '').trim()
                  const ruleRef = f.supportingGuidelineTitle || f.supportingGuidelineCode || f.guideline_reference || ''

                  return (
                    <div
                      key={f.id}
                      className="p-3 rounded-lg border border-border bg-white text-xs space-y-2"
                    >
                      <div className="flex items-center justify-between flex-wrap gap-1">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={f.severity === 'critical' ? 'destructive' : 'warning'}
                            className="text-[9px] uppercase"
                          >
                            {f.severity}
                          </Badge>
                          <span className="font-semibold text-slate-900">{f.category}</span>
                        </div>
                        {ruleRef && (
                          <span className="text-[10px] text-slate-500 font-medium">
                            {ruleRef}
                          </span>
                        )}
                      </div>

                      {offendingText ? (
                        <div className="p-2 rounded bg-rose-50/80 border border-rose-200 text-rose-950 font-mono text-[11px]">
                          <span className="text-rose-500 font-bold mr-1">✕</span>
                          "{offendingText}"
                        </div>
                      ) : (
                        <div className="p-2 rounded bg-slate-50 border border-slate-200 text-slate-500 italic text-[11px]">
                          Offending excerpt not explicitly isolated
                        </div>
                      )}

                      {f.explanation && (
                        <p className="text-slate-600 text-[11px] leading-snug">{f.explanation}</p>
                      )}

                      {suggestedAlternative ? (
                        <div className="p-2 rounded bg-blue-50/70 border border-blue-200 text-blue-950 text-[11px] flex items-start gap-1.5">
                          <CornerDownRight className="w-3.5 h-3.5 text-blue-600 mt-0.5 shrink-0" />
                          <div className="min-w-0 flex-1">
                            <span className="text-[10px] font-semibold text-blue-900 block mb-0.5 uppercase tracking-wide">
                              Suggested Correction
                            </span>
                            <span className="font-sans whitespace-pre-wrap">{suggestedAlternative}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="p-2 rounded bg-slate-50 border border-slate-200 text-slate-500 text-[11px] italic">
                          No automated replacement suggested. Review guideline reference for manual revision.
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          )}

          {/* Tab 3: Approval Timeline */}
          {activeTab === 'timeline' && (
            <div className="overflow-y-auto flex-1 p-2 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-border">
                <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-blue-600" />
                  Chronological Audit Trail & Activity Ledger
                </span>
                <span className="text-[10px] text-slate-400">System-recorded stages & events</span>
              </div>
              <ApprovalTimelineWidget timeline={review.timeline} />
            </div>
          )}

          {/* Tab 4: Reviewer Comments */}
          {activeTab === 'comments' && (
            <div className="space-y-4 overflow-y-auto flex-1 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-border">
                  <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                    Human Reviewer & Team Feedback
                  </span>
                  <span className="text-[10px] text-slate-400">Authentic editorial feedback</span>
                </div>

                {review.comments.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500 bg-slate-50/50 rounded-lg border border-dashed border-slate-200 space-y-1">
                    <MessageSquare className="w-6 h-6 text-slate-300 mx-auto mb-1.5" />
                    <p className="font-semibold text-slate-700">No Reviewer Comments Yet</p>
                    <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                      Automated submission summaries are recorded in the audit timeline. Use the box below to post genuine editorial feedback.
                    </p>
                  </div>
                ) : (
                  review.comments.map((c) => (
                    <div
                      key={c.id}
                      className="p-3 rounded-lg border border-border bg-slate-50/60 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Avatar className="w-5 h-5">
                            <AvatarImage src={c.authorAvatar} />
                            <AvatarFallback>{c.authorName ? c.authorName.slice(0, 2) : 'US'}</AvatarFallback>
                          </Avatar>
                          <span className="font-semibold text-slate-900">{c.authorName}</span>
                          <span className="text-[10px] text-slate-400">({c.authorRole})</span>
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Human Author
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-400 font-mono">{c.timestamp}</span>
                      </div>
                      <p className="text-slate-700 leading-relaxed pl-7">{c.text}</p>
                    </div>
                  ))
                )}
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

      {/* Interactive Full Version History Modal */}
      <VersionHistoryModal
        reviewId={reviewNumericId}
        reviewTitle={review.title}
        isOpen={isVersionHistoryModalOpen}
        onClose={() => setIsVersionHistoryModalOpen(false)}
      />
    </div>
  )
}
