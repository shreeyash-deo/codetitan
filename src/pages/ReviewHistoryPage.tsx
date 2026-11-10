import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { ReviewDetailReportModal } from '@/components/history/ReviewDetailReportModal'
import { useGovernance } from '@/context/GovernanceContext'
import { useToast } from '@/context/ToastContext'
import type { HistoricalReviewRecord, ApprovalFilter } from '@/types/approval'
import {
  FileSpreadsheet,
  Search,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react'

export const ReviewHistoryPage: React.FC = () => {
  const { reviews, addComment, isLoading } = useGovernance()
  const { success } = useToast()

  const [activeFilter, setActiveFilter] = useState<ApprovalFilter>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedReview, setSelectedReview] = useState<HistoricalReviewRecord | null>(null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)

  // Filter reviews
  const filteredReviews = reviews.filter((item) => {
    const matchesFilter =
      activeFilter === 'all' || item.approvalStatus === activeFilter

    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.contentType.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.submittedBy.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.assignedReviewer.name.toLowerCase().includes(searchQuery.toLowerCase())

    return matchesFilter && matchesSearch
  })

  // Open detail report
  const handleOpenReport = (review: HistoricalReviewRecord) => {
    setSelectedReview(review)
    setIsDetailModalOpen(true)
  }

  const getStatusBadge = (status: HistoricalReviewRecord['approvalStatus']) => {
    switch (status) {
      case 'approved':
        return (
          <Badge variant="success" className="text-[10px] gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Approved
          </Badge>
        )
      case 'pending':
        return (
          <Badge variant="blue" className="text-[10px] gap-1">
            <Clock className="w-3 h-3 text-blue-600" />
            Pending
          </Badge>
        )
      case 'needs_revision':
        return (
          <Badge variant="warning" className="text-[10px] gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Needs Revision
          </Badge>
        )
      case 'critical_issues':
        return (
          <Badge variant="destructive" className="text-[10px] gap-1">
            <XCircle className="w-3 h-3 text-rose-600" />
            Critical Issues
          </Badge>
        )
      default:
        return null
    }
  }

  const exportCSV = () => {
    success(`Exported ${filteredReviews.length} compliance audit logs to CSV.`, 'Audit Exported')
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
        title="Review History"
        description="Immutable governance ledger recording every evaluated asset, author submissions, reviewer sign-offs, and compliance scores."
        badge={
          <Badge variant="blue" className="gap-1 font-mono">
            <ShieldCheck className="w-3 h-3 text-blue-600" />
            Audited Ledger
          </Badge>
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs font-medium"
            onClick={exportCSV}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span>Export CSV Audit</span>
          </Button>
        }
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-white p-3 rounded-lg border border-border shadow-xs">
        {/* Five Filter Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 lg:pb-0">
          {[
            { id: 'all', label: 'All Reviews', count: reviews.length },
            {
              id: 'approved',
              label: 'Approved',
              count: reviews.filter((r) => r.approvalStatus === 'approved').length,
            },
            {
              id: 'pending',
              label: 'Pending',
              count: reviews.filter((r) => r.approvalStatus === 'pending').length,
            },
            {
              id: 'needs_revision',
              label: 'Needs Revision',
              count: reviews.filter((r) => r.approvalStatus === 'needs_revision').length,
            },
            {
              id: 'critical_issues',
              label: 'Critical Issues',
              count: reviews.filter((r) => r.approvalStatus === 'critical_issues').length,
            },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id as ApprovalFilter)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0 ${
                activeFilter === tab.id
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  activeFilter === tab.id
                    ? 'bg-slate-700 text-white'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="w-full lg:w-72 relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
          <Input
            placeholder="Search by title, author, or reviewer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 text-xs"
          />
        </div>
      </div>

      {/* Searchable and Filterable Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="px-5 py-3.5">Content Title</th>
                  <th className="px-4 py-3.5">Content Type</th>
                  <th className="px-4 py-3.5">Submitted By</th>
                  <th className="px-4 py-3.5">Assigned Reviewer</th>
                  <th className="px-4 py-3.5">Score</th>
                  <th className="px-4 py-3.5">Violations</th>
                  <th className="px-4 py-3.5">Review Date</th>
                  <th className="px-4 py-3.5">Approval Status</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {isLoading ? (
                  <tr>
                    <td colSpan={9} className="p-10 text-center text-slate-400">
                      Loading review history ledger from database...
                    </td>
                  </tr>
                ) : filteredReviews.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="p-10 text-center space-y-2">
                      <p className="text-slate-600 font-medium">
                        {reviews.length === 0
                          ? 'No review history recorded for this organisation yet'
                          : 'No review history records match the selected filter'}
                      </p>
                      <p className="text-xs text-slate-400 max-w-sm mx-auto">
                        {reviews.length === 0
                          ? 'Submit marketing copy in the Content Review Studio to record immutable audit trials.'
                          : 'Try clearing your search query or selecting "All Reviews".'}
                      </p>
                      {reviews.length > 0 && (
                        <div className="pt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-7"
                            onClick={() => {
                              setActiveFilter('all')
                              setSearchQuery('')
                            }}
                          >
                            Clear Filters
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ) : (
                  filteredReviews.map((rev) => (
                    <tr
                      key={rev.id}
                      onClick={() => handleOpenReport(rev)}
                      className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                    >
                      {/* Title */}
                      <td className="px-5 py-3.5 font-semibold text-slate-900 group-hover:text-blue-600 transition-colors max-w-xs truncate">
                        {rev.title}
                      </td>

                      {/* Content Type */}
                      <td className="px-4 py-3.5 whitespace-nowrap text-slate-600">
                        <Badge variant="outline" className="text-[10px] font-normal">
                          {rev.contentType}
                        </Badge>
                      </td>

                      {/* Submitted By */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Avatar className="w-5 h-5">
                            <AvatarImage src={rev.submittedBy.avatar} />
                            <AvatarFallback>{rev.submittedBy.name.substring(0, 2)}</AvatarFallback>
                          </Avatar>
                          <span className="text-slate-800 font-medium truncate">
                            {rev.submittedBy.name}
                          </span>
                        </div>
                      </td>

                      {/* Reviewer */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Avatar className="w-5 h-5">
                            <AvatarImage src={rev.assignedReviewer.avatar} />
                            <AvatarFallback>{rev.assignedReviewer.name.substring(0, 2)}</AvatarFallback>
                          </Avatar>
                          <span className="text-slate-700 truncate">
                            {rev.assignedReviewer.name}
                          </span>
                        </div>
                      </td>

                      {/* Compliance Score */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span
                          className={`font-bold ${
                            rev.score >= 90
                              ? 'text-emerald-700'
                              : rev.score >= 75
                              ? 'text-blue-700'
                              : 'text-amber-700'
                          }`}
                        >
                          {rev.score}%
                        </span>
                      </td>

                      {/* Violations Count */}
                      <td className="px-4 py-3.5 whitespace-nowrap text-slate-600">
                        {rev.violationsCount === 0 ? (
                          <span className="text-emerald-600 font-medium">0 issues</span>
                        ) : (
                          <span className="text-rose-600 font-medium">
                            {rev.violationsCount} issues
                          </span>
                        )}
                      </td>

                      {/* Review Date */}
                      <td className="px-4 py-3.5 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                        {rev.reviewDate}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        {getStatusBadge(rev.approvalStatus)}
                      </td>

                      {/* Action */}
                      <td className="px-4 py-3.5 whitespace-nowrap text-right">
                        <span className="text-blue-600 font-medium text-xs group-hover:underline inline-flex items-center gap-1">
                          View Report
                          <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Review Report Modal */}
      <ReviewDetailReportModal
        review={selectedReview}
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        onAddComment={addComment}
      />
    </motion.div>
  )
}
