import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
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
import { useToast } from '@/context/ToastContext'
import { workspaceService, type JoinRequest, type WorkspaceMemberInfo } from '@/services/workspaceService'
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
  Users,
  Shield,
  Copy,
  X,
  Check,
  ShieldAlert,
} from 'lucide-react'

export const TeamApprovalsPage: React.FC = () => {
  const navigate = useNavigate()
  const { reviews, approveContent, requestChanges, addComment, isLoading } = useGovernance()
  const { user } = useAuth()
  const { currentWorkspace } = useWorkspace()
  const { success, error: toastError } = useToast()

  const isAdmin = currentWorkspace?.role?.toLowerCase() === 'admin'
  const isReviewerOrAdmin =
    isAdmin || currentWorkspace?.role?.toLowerCase() === 'reviewer'

  const [topTab, setTopTab] = useState<'content' | 'team'>('content')
  const [activeTab, setActiveTab] = useState<'pending' | 'all' | 'needs_revision' | 'approved'>('pending')
  const [targetReviewForChanges, setTargetReviewForChanges] = useState<HistoricalReviewRecord | null>(null)
  const [targetReviewForComment, setTargetReviewForComment] = useState<HistoricalReviewRecord | null>(null)
  const [selectedReviewForModal, setSelectedReviewForModal] = useState<HistoricalReviewRecord | null>(null)

  // Team & Member Access state
  const [joinRequests, setJoinRequests] = useState<JoinRequest[]>([])
  const [members, setMembers] = useState<WorkspaceMemberInfo[]>([])
  const [isLoadingTeam, setIsLoadingTeam] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null)

  const fetchTeamData = useCallback(async () => {
    if (!currentWorkspace?.id) return
    setIsLoadingTeam(true)
    try {
      const [membersData, requestsData] = await Promise.all([
        workspaceService.getMembers(currentWorkspace.id),
        isAdmin
          ? workspaceService.getWorkspaceJoinRequests(currentWorkspace.id).catch(() => [])
          : Promise.resolve([]),
      ])
      setMembers(membersData || [])
      setJoinRequests(requestsData || [])
    } catch {
      // Silently fall back to empty
    } finally {
      setIsLoadingTeam(false)
    }
  }, [currentWorkspace?.id, isAdmin])

  useEffect(() => {
    fetchTeamData()
  }, [fetchTeamData])

  const handleApproveRequest = async (targetUserId: number, userName: string) => {
    if (!currentWorkspace?.id) return
    setActionLoadingId(targetUserId)
    try {
      await workspaceService.approveJoinRequest(currentWorkspace.id, targetUserId)
      success(`${userName} approved as Employee.`, 'Member Approved')
      await fetchTeamData()
    } catch (err: any) {
      toastError(err?.detail || err?.message || 'Failed to approve request.', 'Approval Error')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleRejectRequest = async (targetUserId: number, userName: string) => {
    if (!currentWorkspace?.id) return
    setActionLoadingId(targetUserId)
    try {
      await workspaceService.rejectJoinRequest(currentWorkspace.id, targetUserId)
      success(`Join request for ${userName} rejected and removed.`, 'Request Rejected')
      await fetchTeamData()
    } catch (err: any) {
      toastError(err?.detail || err?.message || 'Failed to reject request.', 'Rejection Error')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleRoleChange = async (targetUserId: number, newRole: 'Employee' | 'Reviewer', userName: string) => {
    if (!currentWorkspace?.id) return
    setActionLoadingId(targetUserId)
    try {
      await workspaceService.updateMemberRole(currentWorkspace.id, targetUserId, newRole)
      success(`${userName}'s role updated to ${newRole}.`, 'Role Updated')
      await fetchTeamData()
    } catch (err: any) {
      toastError(err?.detail || err?.message || 'Failed to update member role.', 'Role Error')
    } finally {
      setActionLoadingId(null)
    }
  }

  const copyOrgId = () => {
    const idToCopy = currentWorkspace?.org_id || currentWorkspace?.orgId
    if (idToCopy) {
      navigator.clipboard.writeText(idToCopy)
      success(`Organisation ID ${idToCopy} copied to clipboard.`, 'Copied')
    }
  }

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

  if (!isReviewerOrAdmin) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto py-16 px-4 text-center space-y-6"
      >
        <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto border border-blue-200 shadow-xs">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-slate-900">Governance & Reviewer Access Restricted</h2>
          <p className="text-xs sm:text-sm text-slate-500 leading-relaxed max-w-lg mx-auto">
            The Team & Approvals dashboard is an administrative control desk for Workspace Reviewers and Admins.
            As an <strong>Employee</strong>, you can track the review status of your submitted copy, view comments, and check approval certificates in <strong>My Submissions</strong>.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Button variant="outline" size="sm" onClick={() => navigate('/')}>
            Back to Dashboard
          </Button>
          <Button variant="primaryBlue" size="sm" onClick={() => navigate('/review-history')}>
            Go to My Submissions
          </Button>
        </div>
      </motion.div>
    )
  }

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
        description="Human governance control tower: Review incoming marketing materials, enforce brand thresholds, request revisions, and manage team membership."
        badge={
          <Badge variant="blue" className="gap-1 font-mono">
            <UserCheck className="w-3.5 h-3.5 text-blue-600" />
            Governance Desk
          </Badge>
        }
      />

      {/* Top Level Section Navigation */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setTopTab('content')}
          className={`py-2.5 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
            topTab === 'content'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <span>Content Approvals</span>
          {pendingCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 text-amber-800 font-bold">
              {pendingCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setTopTab('team')}
          className={`py-2.5 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
            topTab === 'team'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" />
            <span>Organisation & Team Access</span>
          </div>
          {isAdmin && joinRequests.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500 text-white font-bold animate-pulse">
              {joinRequests.length}
            </span>
          )}
        </button>
      </div>

      {topTab === 'content' ? (
        <>
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
                <span className="text-[10px] text-blue-300 font-mono block">TIER 1 • AUTOMATED AI SENTINEL</span>
                <strong className="text-white">BrandShield AI</strong>
                <span className="text-[11px] text-slate-400 block mt-0.5">Deterministic regex & LLM rule scan</span>
              </div>

              <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
                <span className="text-[10px] text-blue-300 font-mono block">TIER 2 • WORKSPACE REVIEWER</span>
                <strong className="text-white">Reviewer / Admin</strong>
                <span className="text-[11px] text-slate-400 block mt-0.5">Compliance inspection & change requests</span>
              </div>

              <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
                <span className="text-[10px] text-blue-300 font-mono block">TIER 3 • EXECUTIVE ADMIN</span>
                <strong className="text-white">
                  {currentWorkspace?.role === 'Admin' ? (user?.name ? `${user.name} (You)` : 'Workspace Admin') : 'Workspace Admin'}
                </strong>
                <span className="text-[11px] text-slate-400 block mt-0.5">Authoritative approval & rule governance</span>
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
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0 cursor-pointer ${
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
                        <div className="flex items-center gap-1.5 justify-end">
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
                          {(item as any).auditStatus && (item as any).auditStatus !== 'verified' && (
                            <span className="text-[10px] px-1 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                              {(item as any).auditStatus}
                            </span>
                          )}
                        </div>
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
                      className="gap-1.5 text-xs text-slate-600 hover:text-slate-900 cursor-pointer"
                      onClick={() => setSelectedReviewForModal(item)}
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Inspect Audit & Timeline</span>
                    </Button>

                    <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1.5 text-xs cursor-pointer"
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
                              className="gap-1.5 text-xs text-amber-700 hover:text-amber-800 hover:bg-amber-50 border-amber-200 cursor-pointer"
                              onClick={() => setTargetReviewForChanges(item)}
                            >
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                              <span>Request Changes</span>
                            </Button>

                            <Button
                              variant="primaryBlue"
                              size="sm"
                              className="gap-1.5 text-xs font-semibold shadow-xs cursor-pointer"
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
        </>
      ) : (
        /* ========================================================================= */
        /* ORGANISATION & TEAM ACCESS TAB                                            */
        /* ========================================================================= */
        <div className="space-y-6">
          {/* Organisation Metadata Banner */}
          <Card className="p-5 border-slate-200 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm text-white shrink-0"
                  style={{ backgroundColor: currentWorkspace?.color || '#0284c7' }}
                >
                  {currentWorkspace?.name?.substring(0, 2).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    {currentWorkspace?.name}
                    <Badge variant="blue" className="text-[10px]">
                      {currentWorkspace?.role || 'Unresolved'}
                    </Badge>
                  </h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-slate-500">Organisation ID:</span>
                    <span className="text-xs font-mono font-semibold text-slate-800">
                      {currentWorkspace?.org_id || currentWorkspace?.orgId || `ORG-${currentWorkspace?.id}`}
                    </span>
                    <button
                      onClick={copyOrgId}
                      className="text-slate-400 hover:text-slate-700 p-0.5 cursor-pointer"
                      title="Copy ORG ID"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              <div className="text-left sm:text-right text-xs text-slate-500">
                <span className="block font-medium text-slate-700">Team Sharing Code</span>
                <span className="text-[11px] text-slate-400">Share this ORG ID with colleagues so they can request to join.</span>
              </div>
            </div>
          </Card>

          {/* ADMIN ONLY: PENDING JOIN REQUESTS */}
          {isAdmin && (
            <Card className="p-5 border-amber-200/80 bg-amber-50/15 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-700">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Pending Join Requests ({joinRequests.length})
                  </h3>
                </div>
                <Badge variant={joinRequests.length > 0 ? 'warning' : 'outline'} className="text-[10px]">
                  {joinRequests.length > 0 ? 'Action Required' : 'All Clear'}
                </Badge>
              </div>

              {joinRequests.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 bg-white/70 rounded-lg border border-slate-200/60">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 mx-auto mb-1.5" />
                  <span>No pending membership requests. New employees joining with this ORG ID will appear here.</span>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {joinRequests.map((req) => (
                    <div
                      key={req.id}
                      className="p-3.5 rounded-lg bg-white border border-amber-200/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarFallback className="bg-amber-100 text-amber-800 text-xs font-bold">
                            {req.name.substring(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="text-xs font-bold text-slate-900">{req.name}</div>
                          <div className="text-[11px] text-slate-500">{req.email}</div>
                          <div className="text-[10px] text-amber-700 font-medium mt-0.5">
                            Requested Role: <span className="font-semibold">{req.role}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-auto">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={actionLoadingId === req.user_id}
                          onClick={() => handleRejectRequest(req.user_id, req.name)}
                          className="text-xs text-rose-700 hover:text-rose-800 hover:bg-rose-50 border-rose-200 cursor-pointer gap-1"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </Button>
                        <Button
                          variant="primaryBlue"
                          size="sm"
                          disabled={actionLoadingId === req.user_id}
                          onClick={() => handleApproveRequest(req.user_id, req.name)}
                          className="text-xs font-semibold cursor-pointer gap-1"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve as Employee</span>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* ACTIVE WORKSPACE MEMBERS */}
          <Card className="p-5 border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-slate-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Active Team Members ({members.length})
                </h3>
              </div>
              <span className="text-xs text-slate-500">
                {isAdmin ? 'Admin Governance Enabled' : 'Member Directory'}
              </span>
            </div>

            {isLoadingTeam ? (
              <div className="p-8 text-center">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600 mx-auto" />
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {members.map((m) => {
                  const isCurrentLoggedUser = String(m.user_id) === String(user?.id)
                  const isMemberAdmin = m.role?.toLowerCase() === 'admin'
                  const isMemberReviewer = m.role?.toLowerCase() === 'reviewer'
                  const isMemberEmployee = m.role?.toLowerCase() === 'employee'
                  const memberName = m.user?.name || m.user_name || `User #${m.user_id}`
                  const memberEmail = m.user?.email || m.user_email || 'Active Member'

                  return (
                    <div
                      key={m.id}
                      className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarFallback className="bg-slate-100 text-slate-700 text-xs font-bold">
                            {memberName.substring(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
                            <span>{memberName}</span>
                            {isCurrentLoggedUser && (
                              <span className="text-[10px] text-slate-400 font-normal">(You)</span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {memberEmail}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 self-end sm:self-auto">
                        <Badge
                          variant={
                            isMemberAdmin
                              ? 'blue'
                              : isMemberReviewer
                              ? 'warning'
                              : 'outline'
                          }
                          className="text-[10px] capitalize font-semibold"
                        >
                          {m.role}
                        </Badge>

                        {/* Admin Role Management (Employee <-> Reviewer) */}
                        {isAdmin && !isMemberAdmin && (
                          <div className="flex items-center gap-1.5">
                            {isMemberEmployee && (
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={actionLoadingId === m.user_id}
                                onClick={() =>
                                  handleRoleChange(m.user_id, 'Reviewer', memberName)
                                }
                                className="text-[11px] text-blue-700 hover:text-blue-800 hover:bg-blue-50 border-blue-200 h-7 cursor-pointer"
                              >
                                Promote to Reviewer
                              </Button>
                            )}
                            {isMemberReviewer && (
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={actionLoadingId === m.user_id}
                                onClick={() =>
                                  handleRoleChange(m.user_id, 'Employee', memberName)
                                }
                                className="text-[11px] text-slate-600 hover:text-slate-900 hover:bg-slate-100 h-7 cursor-pointer"
                              >
                                Demote to Employee
                              </Button>
                            )}
                          </div>
                        )}

                        {isMemberAdmin && (
                          <span className="text-[11px] text-slate-400 italic">
                            Organisation Owner
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>
        </div>
      )}

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
