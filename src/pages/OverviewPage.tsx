import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useWorkspace } from '@/hooks/useWorkspace'
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
import { ReviewDetailsDrawer } from '@/components/dashboard/ReviewDetailsDrawer'
import { ContentSubmissionModal } from '@/components/dashboard/ContentSubmissionModal'
import type { ReviewItem } from '@/types/review'
import type { HistoricalReviewRecord } from '@/types/approval'
import {
  Sparkles,
  BookOpen,
  ShieldCheck,
  FileCheck2,
  Users2,
  AlertTriangle,
  Shield,
  Download,
} from 'lucide-react'

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { currentWorkspace } = useWorkspace()
  const { reviews, metrics, approveContent, addReview } = useGovernance()
  const { success, info } = useToast()

  const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false)

  // Convert HistoricalReviewRecord into ReviewItem for the dashboard table
  const mappedReviews: ReviewItem[] = reviews.map((r) => ({
    id: r.id,
    title: r.title,
    channel: r.channel,
    contentType: r.contentType,
    author: {
      name: r.submittedBy.name,
      avatar: r.submittedBy.avatar,
      role: r.submittedBy.role,
      email: r.submittedBy.email,
    },
    score: r.score,
    status: r.approvalStatus === 'needs_revision' || r.approvalStatus === 'critical_issues' ? 'flagged' : (r.approvalStatus === 'pending' ? 'in_review' : 'approved'),
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
      info(`Asset marked as ${newStatus}.`, 'Status Updated')
    }
  }

  const handleAddNewReview = (newRev: ReviewItem) => {
    const historicalRecord: HistoricalReviewRecord = {
      id: newRev.id,
      title: newRev.title,
      contentType: newRev.contentType,
      channel: newRev.channel,
      submittedBy: {
        name: newRev.author.name,
        role: newRev.author.role || 'Brand Lead',
        email: newRev.author.email || 'sarah.chen@novapay.io',
        avatar: newRev.author.avatar,
      },
      assignedReviewer: {
        name: 'Sarah Chen',
        role: 'Brand Lead',
        email: 'sarah.chen@novapay.io',
        avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
      },
      score: newRev.score,
      violationsCount: newRev.issuesDetected,
      reviewDate: 'Today',
      approvalStatus: newRev.status === 'approved' ? 'approved' : 'pending',
      originalContent: newRev.contentPreview || '',
      correctedContent: newRev.contentPreview || '',
      findings: newRev.issues || [],
      acceptedSuggestionsCount: 0,
      rejectedSuggestionsCount: 0,
      comments: [],
      timeline: [
        {
          id: `t-${Date.now()}-1`,
          stage: 'Content submitted',
          actorName: newRev.author.name,
          actorRole: 'Author',
          timestamp: 'Just now',
          status: 'completed',
        },
        {
          id: `t-${Date.now()}-2`,
          stage: 'AI review completed',
          actorName: 'BrandShield AI',
          actorRole: 'Automated Sentinel',
          timestamp: 'Just now',
          note: `Audit score: ${newRev.score}/100.`,
          status: 'completed',
        },
        {
          id: `t-${Date.now()}-3`,
          stage: 'Suggestions applied',
          actorName: newRev.author.name,
          actorRole: 'Author',
          timestamp: 'Just now',
          status: 'current',
        },
        {
          id: `t-${Date.now()}-4`,
          stage: 'Approval requested',
          actorName: newRev.author.name,
          actorRole: 'Author',
          timestamp: 'Pending',
          status: 'pending',
        },
        {
          id: `t-${Date.now()}-5`,
          stage: 'Reviewer decision',
          actorName: 'Sarah Chen',
          actorRole: 'Brand Lead',
          timestamp: 'Pending',
          status: 'pending',
        },
        {
          id: `t-${Date.now()}-6`,
          stage: 'Final approval',
          actorName: 'Sarah Chen',
          actorRole: 'Brand Lead',
          timestamp: 'Pending',
          status: 'pending',
        },
      ],
    }

    addReview(historicalRecord)
  }

  const handleExportAudit = () => {
    success(`Official quarterly governance audit report for ${currentWorkspace.name} downloaded.`, 'Audit Exported')
  }

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
              Good afternoon
            </span>
            <span className="text-slate-300">•</span>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-semibold">
              <Shield className="w-3 h-3 text-blue-600" />
              <span>{currentWorkspace.name}</span>
            </div>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            Good afternoon, {currentWorkspace.name}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500">
            Here's an overview of your brand health.
          </p>
        </div>

        <div className="flex items-center gap-2.5 pt-1 sm:pt-0">
          <Button
            variant="outline"
            size="default"
            className="gap-2 text-xs font-medium"
            onClick={() => navigate('/brand-guidelines')}
          >
            <BookOpen className="w-3.5 h-3.5 text-slate-600" />
            <span>Manage Guidelines</span>
          </Button>

          <Button
            variant="primaryBlue"
            size="default"
            className="gap-2 text-xs font-medium shadow-xs"
            onClick={() => setIsSubmitModalOpen(true)}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Review New Content</span>
          </Button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Brand Compliance Score"
          value={`${metrics.overallScore}/100`}
          change="+4.2 pts"
          isPositive={true}
          trendDescription="vs. 30d baseline"
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
          change="+18%"
          isPositive={true}
          trendDescription="assets this month"
          icon={FileCheck2}
          onClick={() => navigate('/review-history')}
        />

        <StatCard
          label="Pending Approvals"
          value={metrics.pendingApprovalsCount}
          change={`${metrics.pendingApprovalsCount} urgent`}
          isPositive={metrics.pendingApprovalsCount <= 2}
          trendDescription="awaiting review"
          icon={Users2}
          onClick={() => navigate('/team-approvals')}
        />

        <StatCard
          label="Critical Issues"
          value={metrics.criticalIssuesCount}
          change={metrics.criticalIssuesCount > 0 ? `${metrics.criticalIssuesCount} blocking` : '0 blocking'}
          isPositive={metrics.criticalIssuesCount === 0}
          trendDescription="requires action"
          icon={AlertTriangle}
          onClick={() => navigate('/team-approvals')}
        />
      </div>

      {/* Brand Health & Issues Breakdown */}
      <div id="brand-health-section" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <BrandHealthGauge score={metrics.overallScore} total={100} trend="+4.2 pts" />
        </div>

        <div className="lg:col-span-5">
          <IssuesBreakdownChart />
        </div>
      </div>

      {/* Recent Reviews Table */}
      <div className="space-y-3">
        <RecentReviewsTable
          reviews={mappedReviews}
          onSelectReview={handleOpenReview}
          onOpenSubmitModal={() => setIsSubmitModalOpen(true)}
        />
      </div>

      {/* Recent Activity & Brand Guidelines Status */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <RecentActivityFeed
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
          <BrandGuidelinesStatusCard
            onManageClick={() => navigate('/brand-guidelines')}
          />
        </div>
      </div>

      {/* Review Details Drawer */}
      <ReviewDetailsDrawer
        review={selectedReview}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onStatusChange={handleStatusChange}
      />

      {/* Content Submission Modal */}
      <ContentSubmissionModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        onAddReview={handleAddNewReview}
      />
    </motion.div>
  )
}
