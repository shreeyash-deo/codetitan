import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useAuth } from '@/context/AuthContext'
import { useGovernance } from '@/context/GovernanceContext'
import { useToast } from '@/context/ToastContext'
import { StatCard } from '@/components/common/StatCard'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { BrandHealthGauge } from '@/components/dashboard/BrandHealthGauge'
import { IssuesBreakdownChart } from '@/components/dashboard/IssuesBreakdownChart'
import { RecentReviewsTable } from '@/components/dashboard/RecentReviewsTable'
import { RecentActivityFeed } from '@/components/dashboard/RecentActivityFeed'
import { BrandGuidelinesStatusCard } from '@/components/dashboard/BrandGuidelinesStatusCard'
import { EmployeeWorkflowCard } from '@/components/dashboard/EmployeeWorkflowCard'
import { ReviewDetailsDrawer } from '@/components/dashboard/ReviewDetailsDrawer'
import type { ReviewItem } from '@/types/review'
import {
  Sparkles,
  BookOpen,
  ShieldCheck,
  FileCheck2,
  Users2,
  AlertTriangle,
  Shield,
  ArrowRight,
  UploadCloud,
  CheckCircle2,
} from 'lucide-react'

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { currentWorkspace } = useWorkspace()
  const { user } = useAuth()
  const { reviews, metrics, approveContent, isLoading } = useGovernance()
  const { info } = useToast()

  const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  const userRole = (currentWorkspace?.role || '').toLowerCase()
  const isAdmin = userRole === 'admin'
  const isEmployee = userRole === 'employee' || userRole === 'editor'

  const myTotalReviews = reviews.length
  const myPendingCount = reviews.filter((r) => r.approvalStatus === 'pending').length
  const myNeedsRevisionCount = reviews.filter(
    (r) => r.approvalStatus === 'needs_revision' || r.approvalStatus === 'critical_issues'
  ).length
  const myApprovedCount = reviews.filter((r) => r.approvalStatus === 'approved').length

  // Convert HistoricalReviewRecord into ReviewItem for the dashboard table
  const mappedReviews: ReviewItem[] = reviews.map((r) => ({
    id: r.id,
    title: r.title,
    channel: r.channel || 'Social',
    contentType: r.contentType,
    author: {
      name: r.submittedBy.name,
      avatar: r.submittedBy.avatar,
      role: r.submittedBy.role,
      email: r.submittedBy.email,
    },
    score: r.score,
    status:
      r.approvalStatus === 'needs_revision' || r.approvalStatus === 'critical_issues'
        ? 'flagged'
        : r.approvalStatus === 'pending'
        ? 'in_review'
        : 'approved',
    issuesDetected: r.violationsCount,
    submittedAt: r.reviewDate,
    date: r.reviewDate,
    brandGuidelineId: 'bg-voice',
    summary: r.originalContent,
    contentPreview: r.originalContent,
    issues: r.findings,
  }))

  const handleOpenReview = (review: ReviewItem) => {
    setSelectedReview(review)
    setIsDrawerOpen(true)
  }

  const handleStatusChange = (reviewId: string, newStatus: ReviewItem['status']) => {
    if (newStatus === 'approved') {
      approveContent(reviewId)
    } else {
      info(`Asset status updated to ${newStatus}.`, 'Status Updated')
    }
  }

  const isBrandNewOrg =
    !isLoading &&
    metrics.contentReviewedCount === 0 &&
    metrics.approvedRulesCount === 0 &&
    metrics.sourceDocsCount === 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-border/80">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Workspace Overview
            </span>
            <span className="text-slate-300">•</span>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-semibold border border-blue-100">
              <Shield className="w-3 h-3 text-blue-600" />
              <span>{currentWorkspace?.name || 'Organisation'}</span>
              {currentWorkspace?.orgId && (
                <span className="text-[10px] text-blue-500 font-mono">({currentWorkspace.orgId})</span>
              )}
            </div>
            {currentWorkspace?.role && (
              <Badge variant="outline" className="text-[10px] uppercase font-semibold">
                {currentWorkspace.role}
              </Badge>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            Welcome, {user?.name || currentWorkspace?.name || 'Operator'}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500">
            {isEmployee
              ? `Your personal compliance overview, submissions, and approval status for ${currentWorkspace?.name || 'your organisation'}.`
              : `Real-time compliance posture and brand governance telemetry for ${currentWorkspace?.name || 'your organisation'}.`}
          </p>
        </div>

        <div className="flex items-center gap-2.5 pt-1 sm:pt-0">
          {isAdmin && (
            <Button
              variant="outline"
              size="default"
              className="gap-2 text-xs font-medium"
              onClick={() => navigate('/brand-guidelines')}
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-600" />
              <span>Manage Guidelines</span>
            </Button>
          )}

          {isEmployee && (
            <Button
              variant="outline"
              size="default"
              className="gap-2 text-xs font-medium"
              onClick={() => navigate('/brand-guidelines')}
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-600" />
              <span>Brand Guidelines</span>
            </Button>
          )}

          <Button
            variant="primaryBlue"
            size="default"
            className="gap-2 text-xs font-medium shadow-xs"
            onClick={() => navigate('/content-review')}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Review New Content</span>
          </Button>
        </div>
      </div>

      {/* Onboarding Banner for newly created organisation */}
      {isBrandNewOrg && (
        <div className="p-5 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50/80 via-indigo-50/40 to-slate-50 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-600 text-white">
                  Getting Started
                </span>
                <span className="text-xs font-semibold text-slate-900">
                  Welcome to {currentWorkspace?.name || 'BrandShield'}
                </span>
              </div>
              <p className="text-xs text-slate-600 max-w-2xl leading-relaxed">
                {isEmployee
                  ? 'Your workspace is ready. You can submit marketing copy, ad creative, or blog articles to run automated compliance audits against approved brand guidelines and request reviewer approvals.'
                  : 'Establish your Brand Memory by uploading your corporate brand guidelines, editorial stylebooks, or terminology guides. Our AI engine extracts candidate rules for Admin approval, creating authoritative guardrails for all marketing copy.'}
              </p>
              {!isEmployee ? (
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-1">
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px]">1</span>
                    Upload Guidelines (PDF/DOCX)
                  </span>
                  <span className="text-slate-300">→</span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px]">2</span>
                    Approve Brand Rules
                  </span>
                  <span className="text-slate-300">→</span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px]">3</span>
                    Scan & Remediate Copy
                  </span>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-1">
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px]">1</span>
                    Review New Content Studio
                  </span>
                  <span className="text-slate-300">→</span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px]">2</span>
                    Inspect AI Findings & Remediate
                  </span>
                  <span className="text-slate-300">→</span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px]">3</span>
                    Submit for Reviewer Sign-Off
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2.5 shrink-0">
              <Button
                variant="primaryBlue"
                size="sm"
                className="text-xs gap-1.5 shadow-xs"
                onClick={() => navigate(isEmployee ? '/content-review' : '/brand-guidelines')}
              >
                {isEmployee ? <Sparkles className="w-3.5 h-3.5" /> : <UploadCloud className="w-3.5 h-3.5" />}
                <span>{isEmployee ? 'Start Review' : 'Upload Guidelines'}</span>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 4 Live Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isEmployee ? (
          <>
            <StatCard
              label="My Compliance Score"
              value={metrics.hasReviews ? `${metrics.overallScore}/100` : '--'}
              change={
                metrics.hasReviews
                  ? metrics.overallScore >= 80
                    ? 'Healthy posture'
                    : 'Attention needed'
                  : 'Awaiting submissions'
              }
              isPositive={metrics.overallScore >= 80}
              trendDescription="average on your copy"
              icon={ShieldCheck}
              highlight={true}
              onClick={() => {
                const el = document.getElementById('brand-health-section')
                el?.scrollIntoView({ behavior: 'smooth' })
              }}
            />

            <StatCard
              label="My Submissions"
              value={myTotalReviews}
              change={myTotalReviews > 0 ? `${myTotalReviews} submitted` : 'No submissions yet'}
              isPositive={true}
              trendDescription="assets created by you"
              icon={FileCheck2}
              onClick={() => navigate('/review-history')}
            />

            <StatCard
              label="Awaiting Approval"
              value={myPendingCount}
              change={myPendingCount > 0 ? `${myPendingCount} awaiting sign-off` : 'All cleared'}
              isPositive={myPendingCount === 0}
              trendDescription="in reviewer queue"
              icon={Users2}
              onClick={() => navigate('/review-history?filter=pending')}
            />

            <StatCard
              label={myNeedsRevisionCount > 0 ? 'Needs Revision' : 'Approved Assets'}
              value={myNeedsRevisionCount > 0 ? myNeedsRevisionCount : myApprovedCount}
              change={
                myNeedsRevisionCount > 0
                  ? `${myNeedsRevisionCount} require edits`
                  : `${myApprovedCount} certified ready`
              }
              isPositive={myNeedsRevisionCount === 0}
              trendDescription={
                myNeedsRevisionCount > 0
                  ? 'reviewer feedback provided'
                  : 'ready for publication'
              }
              icon={myNeedsRevisionCount > 0 ? AlertTriangle : CheckCircle2}
              onClick={() =>
                navigate(
                  myNeedsRevisionCount > 0
                    ? '/review-history?filter=needs_revision'
                    : '/review-history?filter=approved'
                )
              }
            />
          </>
        ) : (
          <>
            <StatCard
              label="Brand Compliance Score"
              value={metrics.hasReviews ? `${metrics.overallScore}/100` : '--'}
              change={
                metrics.hasReviews
                  ? metrics.overallScore >= 80
                    ? 'Healthy posture'
                    : 'Attention needed'
                  : 'Awaiting audits'
              }
              isPositive={metrics.overallScore >= 80}
              trendDescription={metrics.hasReviews ? 'based on live reviews' : 'review copy to set baseline'}
              icon={ShieldCheck}
              highlight={true}
              onClick={() => {
                const el = document.getElementById('brand-health-section')
                el?.scrollIntoView({ behavior: 'smooth' })
              }}
            />

            <StatCard
              label="Content Reviewed"
              value={metrics.contentReviewedCount}
              change={metrics.contentReviewedCount > 0 ? `${metrics.contentReviewedCount} audited` : 'No audits yet'}
              isPositive={true}
              trendDescription="assets scanned in org"
              icon={FileCheck2}
              onClick={() => navigate('/review-history')}
            />

            <StatCard
              label="Pending Approvals"
              value={metrics.pendingApprovalsCount}
              change={metrics.pendingApprovalsCount > 0 ? `${metrics.pendingApprovalsCount} awaiting sign-off` : 'All cleared'}
              isPositive={metrics.pendingApprovalsCount <= 2}
              trendDescription="requires managerial review"
              icon={Users2}
              onClick={() => navigate('/team-approvals')}
            />

            <StatCard
              label="Approved Brand Rules"
              value={metrics.approvedRulesCount}
              change={metrics.pendingCandidatesCount > 0 ? `${metrics.pendingCandidatesCount} pending candidates` : 'All rules active'}
              isPositive={metrics.pendingCandidatesCount === 0}
              trendDescription="authoritative rules"
              icon={BookOpen}
              onClick={() => navigate('/brand-guidelines')}
            />
          </>
        )}
      </div>

      {/* Brand Health & Issues Breakdown */}
      <div id="brand-health-section" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <BrandHealthGauge
            score={metrics.overallScore}
            total={100}
            hasReviews={metrics.hasReviews}
            orgName={currentWorkspace?.name || 'Organisation'}
            activeRulesCount={metrics.approvedRulesCount}
            isEmployee={isEmployee}
          />
        </div>

        <div className="lg:col-span-5">
          <IssuesBreakdownChart issues={metrics.violationsByCategory} isEmployee={isEmployee} />
        </div>
      </div>

      {/* Recent Reviews Table */}
      <div className="space-y-3">
        <RecentReviewsTable
          reviews={mappedReviews}
          onSelectReview={handleOpenReview}
          onOpenSubmitModal={() => navigate('/content-review')}
          isEmployee={isEmployee}
        />
      </div>

      {/* Recent Activity & Right Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <RecentActivityFeed
            activity={metrics.recentActivity}
            onSelectActivityTarget={(targetId) => {
              const found = mappedReviews.find((r) => r.id === targetId)
              if (found) {
                setSelectedReview(found)
                setIsDrawerOpen(true)
              }
            }}
          />
        </div>

        <div className="lg:col-span-5">
          {isEmployee ? (
            <EmployeeWorkflowCard
              pendingCount={myPendingCount}
              needsRevisionCount={myNeedsRevisionCount}
              approvedCount={myApprovedCount}
              activeRulesCount={metrics.approvedRulesCount}
            />
          ) : (
            <BrandGuidelinesStatusCard
              approvedRules={metrics.approvedRulesCount}
              pendingRules={metrics.pendingCandidatesCount}
              sourceDocsCount={metrics.sourceDocsCount}
              onManageClick={() => navigate('/brand-guidelines')}
            />
          )}
        </div>
      </div>

      {/* Review Details Drawer */}
      <ReviewDetailsDrawer
        review={selectedReview}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onStatusChange={handleStatusChange}
        userRole={currentWorkspace?.role}
      />
    </motion.div>
  )
}
