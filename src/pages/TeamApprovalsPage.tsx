import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { PageHeader } from '@/components/common/PageHeader'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { RequestChangesDialog } from '@/components/approvals/RequestChangesDialog'
import { AddCommentDialog } from '@/components/approvals/AddCommentDialog'
import { ReviewDetailReportModal } from '@/components/history/ReviewDetailReportModal'
import { useGovernance } from '@/context/GovernanceContext'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useAuth } from '@/context/AuthContext'
import type { HistoricalReviewRecord } from '@/types/approval'
import {
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  MessageSquare,
  Clock,
  GitBranch,
  Eye,
  ShieldCheck,
  Loader2,
} from 'lucide-react'

export const TeamApprovalsPage: React.FC = () => {
  const { reviews, approveContent, requestChanges, addComment, isLoading } = useGovernance()
  const { user } = useAuth()
  const { currentWorkspace } = useWorkspace()

  const isReviewerOrAdmin =
    currentWorkspace?.role?.toLowerCase() === 'admin' ||
    currentWorkspace?.role?.toLowerCase() === 'reviewer'

  const [activeTab, setActiveTab] = useState<'pending' | 'all' | 'needs_revision' | 'approved'>('pending')
  const [targetReviewForChanges, setTargetReviewForChanges] = useState<HistoricalReviewRecord | null>(null)
  const [targetReviewForComment, setTargetReviewForComment] = useState<HistoricalReviewRecord | null>(null)
  const [selectedReviewForModal, setSelectedReviewForModal] = useState<HistoricalReviewRecord | null>(null)

  // Filter queue
  const displayedReviews = reviews.filter((r) => {
    if (activeTab === 'pending') return r.approvalStatus === 'pending' || r.approvalStatus === 'critical_issues'
    if (activeTab === 'needs_revision') return r.approvalStatus === 'needs_revision'
    if (activeTab === 'approved') return r.approvalStatus === 'approved'
    return true
  })

  const pendingCount = reviews.filter(
    (r) => r.approvalStatus === 'pending' || r.approvalStatus === 'critical_issues'
  ).length
  const revisionCount = reviews.filter((r) => r.approvalStatus === 'needs_revision').length
  const approvedCount = reviews.filter((r) => r.approvalStatus === 'approved').length

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      {/* Page Header */}
      <PageHeader
        title="Team & Approvals Dashboard"
        description="Human governance control tower: Review incoming marketing materials, enforce brand thresholds, request revisions, and issue publishing clearances."
        badge={
          <Badge variant="blue" className="gap-1 font-mono">
            <UserCheck className="w-3.5 h-3.5 text-blue-600" />
            Governance Desk
          </Badge>
        }
      />

      {/* 4 Summary Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-amber-200/80 bg-amber-50/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider">
              Pending Approvals
            </span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {pendingCount}
          </div>
          <p className="text-[11px] text-amber-700 mt-1">Requires reviewer sign-off</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Needs Revision
            </span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {revisionCount}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Returned to content creators</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Approved Assets
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {approvedCount}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Certified for publication</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Avg. Turnaround
            </span>
            <span className="text-xs font-mono text-emerald-600 font-bold">-22% faster</span>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            1.8 hrs
          </div>
          <p className="text-[11px] text-slate-500 mt-1">From upload to sign-off</p>
        </Card>
      </div>

      {/* Multi-Tier Review Hierarchy Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white border border-slate-800 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Active Sign-Off Routing Protocol
            </span>
          </div>
          <Badge variant="blue" className="text-[10px]">
            Strict Tier 3 Enabled
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
            <span className="text-[10px] text-blue-300 font-mono block">TIER 1 • CREATIVE AUDIT</span>
            <strong className="text-white">Elena Rostova</strong>
            <span className="text-[11px] text-slate-400 block mt-0.5">Logo, clearspace & visual palette</span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
            <span className="text-[10px] text-blue-300 font-mono block">TIER 2 • LEGAL & CLAIMS</span>
            <strong className="text-white">Marcus Vance</strong>
            <span className="text-[11px] text-slate-400 block mt-0.5">Statutory disclaimers & FX terms</span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
            <span className="text-[10px] text-blue-300 font-mono block">TIER 3 • EXECUTIVE SIGN-OFF</span>
            <strong className="text-white">Sarah Chen (Brand Lead)</strong>
            <span className="text-[11px] text-slate-400 block mt-0.5">Final publishing authorization token</span>
          </div>
        </div>
      </div>

      {/* Approval Filter Bar */}
      <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-border shadow-xs">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { id: 'pending', label: 'Pending Review Queue', count: pendingCount },
            { id: 'needs_revision', label: 'Needs Revision', count: revisionCount },
            { id: 'approved', label: 'Approved Materials', count: approvedCount },
            { id: 'all', label: 'All Items', count: reviews.length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0 ${
                activeTab === tab.id
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  activeTab === tab.id
                    ? 'bg-slate-700 text-white'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Employee Role Notice if not Reviewer/Admin */}
      {!isReviewerOrAdmin && (
        <div className="p-3.5 rounded-lg bg-blue-50/70 border border-blue-200 text-xs text-blue-900 flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0" />
          <span>
            You are signed in with the <strong>Employee</strong> role in this organisation. Submissions can be inspected and commented on, but publishing approvals and change requests require <strong>Reviewer</strong> or <strong>Admin</strong> privileges.
          </span>
        </div>
      )}

      {/* Approval Requests Cards */}
      <div className="space-y-4">
        {isLoading ? (
          <Card className="p-12 text-center space-y-2">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
            <h4 className="text-sm font-bold text-slate-900">Loading Governance Queue...</h4>
            <p className="text-xs text-slate-500">Retrieving active submissions and approvals</p>
          </Card>
        ) : displayedReviews.length === 0 ? (
          <Card className="p-12 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <h4 className="text-sm font-bold text-slate-900">
              {reviews.length === 0 ? 'No Submissions in this Organisation' : 'Queue is Clear'}
            </h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {reviews.length === 0
                ? 'Submit marketing copy from the Content Review Studio to initiate the review and sign-off workflow.'
                : 'There are no content approval requests matching this filter.'}
            </p>
          </Card>
        ) : (
          displayedReviews.map((item) => (
            <Card
              key={item.id}
              className="p-5 hover:border-slate-300 transition-all shadow-xs space-y-4"
            >
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge
                      variant={
                        item.approvalStatus === 'approved'
                          ? 'success'
                          : item.approvalStatus === 'needs_revision'
                          ? 'warning'
                          : item.approvalStatus === 'critical_issues'
                          ? 'destructive'
                          : 'blue'
                      }
                      className="text-[10px]"
                    >
                      {item.approvalStatus.replace('_', ' ').toUpperCase()}
                    </Badge>
                    <Badge variant="outline" className="text-[10px]">
                      {item.contentType}
                    </Badge>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Submitted {item.reviewDate}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900">
                    {item.title}
                  </h3>
                </div>

                {/* Score Pill */}
                <div className="flex sm:flex-col items-center sm:items-end justify-between shrink-0">
                  <div className="text-left sm:text-right">
                    <span
                      className={`text-xl font-bold ${
                        item.score >= 90
                          ? 'text-emerald-700'
                          : item.score >= 75
                          ? 'text-blue-700'
                          : 'text-amber-700'
                      }`}
                    >
                      {item.score}%
                    </span>
                    <span className="text-[10px] text-slate-400 block">Compliance</span>
                  </div>
                </div>
              </div>

              {/* Creator & Reviewer Metadata */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-slate-50/70 border border-slate-200/80 text-xs">
                <div className="flex items-center gap-2.5">
                  <Avatar className="w-6 h-6">
                    <AvatarImage src={item.submittedBy.avatar} />
                    <AvatarFallback>{item.submittedBy.name.substring(0, 2)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                      Content Creator
                    </span>
                    <span className="font-semibold text-slate-800">
                      {item.submittedBy.name}
                    </span>
                    <span className="text-slate-400 text-[11px] ml-1">({item.submittedBy.role})</span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5">
                  <Avatar className="w-6 h-6">
                    <AvatarImage src={item.assignedReviewer.avatar} />
                    <AvatarFallback>{item.assignedReviewer.name.substring(0, 2)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                      Assigned Reviewer
                    </span>
                    <span className="font-semibold text-slate-800">
                      {item.assignedReviewer.name}
                    </span>
                    <span className="text-slate-400 text-[11px] ml-1">({item.assignedReviewer.role})</span>
                  </div>
                </div>
              </div>

              {/* Working Content Preview */}
              <div className="p-3 rounded-md bg-white border border-slate-200 text-xs text-slate-700 leading-relaxed font-serif italic">
                "{item.correctedContent || item.originalContent}"
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-xs text-slate-600 hover:text-slate-900"
                  onClick={() => setSelectedReviewForModal(item)}
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Inspect Audit & Timeline</span>
                </Button>

                <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={() => setTargetReviewForComment(item)}
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Add Comments ({item.comments.length})</span>
                  </Button>

                  {item.approvalStatus !== 'approved' && (
                    isReviewerOrAdmin ? (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1.5 text-xs text-amber-700 hover:text-amber-800 hover:bg-amber-50 border-amber-200"
                          onClick={() => setTargetReviewForChanges(item)}
                        >
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                          <span>Request Changes</span>
                        </Button>

                        <Button
                          variant="primaryBlue"
                          size="sm"
                          className="gap-1.5 text-xs font-semibold shadow-xs"
                          onClick={() => approveContent(item.id)}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Approve Content</span>
                        </Button>
                      </>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-md border border-slate-200">
                        <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                        <span>Reviewer Sign-off Required</span>
                      </span>
                    )
                  )}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Request Changes Dialog */}
      <RequestChangesDialog
        review={targetReviewForChanges}
        isOpen={Boolean(targetReviewForChanges)}
        onClose={() => setTargetReviewForChanges(null)}
        onSubmitChanges={requestChanges}
      />

      {/* Add Comment Dialog */}
      <AddCommentDialog
        review={targetReviewForComment}
        isOpen={Boolean(targetReviewForComment)}
        onClose={() => setTargetReviewForComment(null)}
        onAddComment={addComment}
      />

      {/* Detailed Report Modal */}
      <ReviewDetailReportModal
        review={selectedReviewForModal}
        isOpen={Boolean(selectedReviewForModal)}
        onClose={() => setSelectedReviewForModal(null)}
        onAddComment={addComment}
      />
    </motion.div>
  )
}
