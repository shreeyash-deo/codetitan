import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react'
import type { HistoricalReviewRecord } from '@/types/approval'
import type {
  ApprovedRule,
  PendingCandidateRule,
  SourceDocument,
  GuidelineCategory,
} from '@/types/guidelines'
import {
  guidelineService,
  approvalService,
  historyService,
  authService,
  apiClient,
} from '@/services'
import { brandService, type BrandTelemetry, type ViolationCategoryStat, type DashboardActivityItem } from '@/services/brandService'
import { mockHistoricalReviews } from '@/data/mockHistoricalReviews'
import {
  initialApprovedRules,
  initialPendingCandidates,
  initialSourceDocuments,
} from '@/data/mockKnowledgeBase'
import { useToast } from './ToastContext'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useAuth } from './AuthContext'

interface GovernanceContextValue {
  // Loading & error state
  isLoading: boolean
  error: string | null
  refreshData: () => Promise<void>

  // Reviews & Approvals
  reviews: HistoricalReviewRecord[]
  addReview: (newReview: HistoricalReviewRecord) => void
  approveContent: (reviewId: string) => Promise<void>
  requestChanges: (reviewId: string, notes: string) => Promise<void>
  addComment: (reviewId: string, commentText: string) => Promise<void>

  // Guidelines & Knowledge Base
  approvedRules: ApprovedRule[]
  pendingCandidates: PendingCandidateRule[]
  sourceDocuments: SourceDocument[]
  addApprovedRule: (rule: ApprovedRule) => Promise<void>
  updateApprovedRule: (rule: ApprovedRule) => Promise<void>
  deleteApprovedRule: (ruleId: string) => Promise<void>
  approveCandidateRule: (candidateId: string) => Promise<void>
  rejectCandidateRule: (candidateId: string) => Promise<void>
  approveAllHighConfidenceCandidates: () => void
  uploadSourceDocument: (doc: SourceDocument) => Promise<void>
  uploadDocumentFile: (file: File) => Promise<void>
  reExtractDocument: (docId: string) => Promise<void>
  deleteSourceDocument: (docId: string) => Promise<void>

  // Telemetry Metrics
  metrics: {
    overallScore: number
    hasReviews: boolean
    contentReviewedCount: number
    pendingApprovalsCount: number
    criticalIssuesCount: number
    approvedRulesCount: number
    pendingCandidatesCount: number
    sourceDocsCount: number
    violationsByCategory: ViolationCategoryStat[]
    recentActivity: DashboardActivityItem[]
  }
}

const GovernanceContext = createContext<GovernanceContextValue | undefined>(undefined)

export const GovernanceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { success, info, warning, error: toastError } = useToast()
  const { currentWorkspace } = useWorkspace()
  const { user } = useAuth()

  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // 1. Shared Reviews State
  const [reviews, setReviews] = useState<HistoricalReviewRecord[]>(
    apiClient.isMockMode() ? mockHistoricalReviews : []
  )

  // 2. Shared Guidelines State
  const [approvedRules, setApprovedRules] = useState<ApprovedRule[]>(
    apiClient.isMockMode() ? initialApprovedRules : []
  )
  const [pendingCandidates, setPendingCandidates] = useState<PendingCandidateRule[]>(
    apiClient.isMockMode() ? initialPendingCandidates : []
  )
  const [sourceDocuments, setSourceDocuments] = useState<SourceDocument[]>(
    apiClient.isMockMode() ? initialSourceDocuments : []
  )
  const [telemetry, setTelemetry] = useState<BrandTelemetry | null>(null)

  const refreshData = useCallback(async () => {
    if (apiClient.isMockMode()) return
    if (!currentWorkspace) {
      setApprovedRules([])
      setPendingCandidates([])
      setSourceDocuments([])
      setReviews([])
      setTelemetry(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const brandId = currentWorkspace.id

      const [rulesData, candidatesData, docsData, historyData, telemetryData] = await Promise.all([
        guidelineService.getApprovedRules(brandId),
        guidelineService.getPendingCandidates(brandId),
        guidelineService.getSourceDocuments(brandId),
        historyService.getReviewHistory({ brandId }),
        brandService.getBrandTelemetry(brandId).catch(() => null),
      ])

      if (rulesData) {
        setApprovedRules(rulesData as unknown as ApprovedRule[])
      }
      if (candidatesData) {
        setPendingCandidates(candidatesData as unknown as PendingCandidateRule[])
      }
      if (docsData) {
        setSourceDocuments(docsData as unknown as SourceDocument[])
      }
      if (historyData) {
        setReviews(historyData as unknown as HistoricalReviewRecord[])
      }
      if (telemetryData) {
        setTelemetry(telemetryData)
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.detail || err?.message || 'Failed to fetch live governance data from backend'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [currentWorkspace?.id])

  // Fetch initial data from services
  useEffect(() => {
    refreshData()
  }, [refreshData])

  // Review Actions
  const addReview = (newReview: HistoricalReviewRecord) => {
    setReviews((prev) => [newReview, ...prev])
    info(`"${newReview.title}" added to the review queue.`, 'Review Ingested')
  }

  const approveContent = async (reviewId: string) => {
    const timestamp = 'Just now'
    const authorName = user?.name || 'Reviewer'
    const authorRole = currentWorkspace?.role || 'Reviewer'

    try {
      if (!apiClient.isMockMode()) {
        await approvalService.approveContent(reviewId)
      }

      setReviews((prev) =>
        prev.map((r) => {
          if (r.id === reviewId) {
            const updatedTimeline = r.timeline.map((step) => {
              if (step.stage === 'Reviewer decision' || step.stage === 'Final approval') {
                return { ...step, status: 'completed' as const, timestamp }
              }
              return step
            })

            return {
              ...r,
              approvalStatus: 'approved' as const,
              score: Math.max(r.score, 95),
              violationsCount: 0,
              comments: r.comments,
              timeline: updatedTimeline,
            }
          }
          return r
        })
      )

      success('Asset officially approved and certified for publication!', 'Approval Granted')
      // Background re-fetch to ensure perfect ledger sync
      refreshData()
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.detail || err?.message || 'Failed to approve asset'
      setError(msg)
      toastError(msg, 'Approval Blocked')
      throw err
    }
  }

  const requestChanges = async (reviewId: string, notes: string) => {
    const timestamp = 'Just now'
    const authorName = user?.name || 'Reviewer'
    const authorRole = currentWorkspace?.role || 'Reviewer'

    try {
      if (!apiClient.isMockMode()) {
        await approvalService.requestChanges(reviewId, notes)
      }

      setReviews((prev) =>
        prev.map((r) => {
          if (r.id === reviewId) {
            const newComment = {
              id: `c-${Date.now()}`,
              authorName,
              authorRole,
              authorAvatar: `https://api.dicebear.com/7.x/initials/svg?seed=${authorName}`,
              text: `REVISION REQUESTED: ${notes}`,
              timestamp,
            }

            const updatedTimeline = r.timeline.map((step) => {
              if (step.stage === 'Reviewer decision') {
                return { ...step, status: 'current' as const, note: `Changes requested: ${notes}` }
              }
              return step
            })

            return {
              ...r,
              approvalStatus: 'needs_revision' as const,
              comments: [...r.comments, newComment],
              timeline: updatedTimeline,
            }
          }
          return r
        })
      )

      warning('Revision instructions routed back to the content author.', 'Changes Requested')
      refreshData()
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.detail || err?.message || 'Failed to submit change request'
      setError(msg)
      toastError(msg, 'Revision Request Error')
      throw err
    }
  }

  const addComment = async (reviewId: string, commentText: string) => {
    const authorName = user?.name || 'Reviewer'
    const authorRole = currentWorkspace?.role || 'Member'
    const newComment = {
      id: `c-${Date.now()}`,
      authorName,
      authorRole,
      authorAvatar: `https://api.dicebear.com/7.x/initials/svg?seed=${authorName}`,
      text: commentText,
      timestamp: 'Just now',
    }

    try {
      if (!apiClient.isMockMode()) {
        await approvalService.addComment(reviewId, commentText)
      }

      setReviews((prev) =>
        prev.map((r) => (r.id === reviewId ? { ...r, comments: [...r.comments, newComment] } : r))
      )

      info('Governance memo added to audit trail.', 'Comment Logged')
      refreshData()
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.detail || err?.message || 'Failed to add comment'
      setError(msg)
      toastError(msg, 'Comment Error')
      throw err
    }
  }

  // Guidelines Actions
  const addApprovedRule = async (rule: ApprovedRule) => {
    try {
      if (!apiClient.isMockMode()) {
        await guidelineService.createApprovedRule(rule as any, currentWorkspace?.id)
      }
      setApprovedRules((prev) => [rule, ...prev])
      success(`Rule "${rule.code}: ${rule.title}" added to active brand knowledge.`, 'Rule Created')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create rule')
    }
  }

  const updateApprovedRule = async (rule: ApprovedRule) => {
    try {
      if (!apiClient.isMockMode()) {
        await guidelineService.updateApprovedRule(rule.id, rule as any)
      }
      setApprovedRules((prev) => prev.map((r) => (r.id === rule.id ? rule : r)))
      success(`Rule "${rule.code}" updated successfully.`, 'Rule Updated')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update rule')
    }
  }

  const deleteApprovedRule = async (ruleId: string) => {
    try {
      if (!apiClient.isMockMode()) {
        await guidelineService.deleteApprovedRule(ruleId)
      }
      setApprovedRules((prev) => prev.filter((r) => r.id !== ruleId))
      info('Rule removed from active brand guidelines.', 'Rule Deleted')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rule')
    }
  }

  const approveCandidateRule = async (candidateId: string) => {
    const candidate = pendingCandidates.find((c) => c.id === candidateId)
    if (!candidate) return

    try {
      let promotedRule: ApprovedRule
      if (!apiClient.isMockMode()) {
        const res = await guidelineService.approveCandidate(candidateId)
        promotedRule = {
          id: res.id,
          code: res.code,
          category: res.category as GuidelineCategory,
          subCategory: res.subCategory,
          title: res.title,
          description: res.description,
          enforcementLevel: res.enforcementLevel,
          sourceDocument: res.sourceDocument,
          sourcePage: res.sourcePage,
          lastUpdated: res.lastUpdated,
          updatedBy: res.updatedBy,
        }
      } else {
        const prefixMap: Record<GuidelineCategory, string> = {
          'Brand Voice': 'BV',
          'Terminology': 'TM',
          'Brand Facts': 'BF',
          'Claims & Restrictions': 'CR',
          'Visual Identity': 'VI',
        }
        promotedRule = {
          id: `rule-promoted-${Date.now()}`,
          code: `${prefixMap[candidate.category] || 'RULE'}-${Math.floor(20 + Math.random() * 80)}`,
          category: candidate.category,
          subCategory: candidate.subCategory,
          title: candidate.title,
          description: candidate.extractedText,
          enforcementLevel: candidate.suggestedEnforcement,
          sourceDocument: candidate.sourceDocument,
          sourcePage: candidate.sourceSection,
          lastUpdated: 'Just now',
          updatedBy: 'Sarah Chen (Brand Lead)',
        }
      }

      setApprovedRules((prev) => [promotedRule, ...prev])
      setPendingCandidates((prev) => prev.filter((c) => c.id !== candidateId))

      setSourceDocuments((prev) =>
        prev.map((doc) =>
          doc.name === candidate.sourceDocument
            ? {
                ...doc,
                approvedRulesCount: doc.approvedRulesCount + 1,
                extractedCandidatesCount: Math.max(0, doc.extractedCandidatesCount - 1),
              }
            : doc
        )
      )

      success(`Candidate rule "${candidate.title}" promoted to official brand knowledge!`, 'Rule Approved')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve candidate')
    }
  }

  const rejectCandidateRule = async (candidateId: string) => {
    const candidate = pendingCandidates.find((c) => c.id === candidateId)
    try {
      if (!apiClient.isMockMode()) {
        await guidelineService.rejectCandidate(candidateId)
      }
      setPendingCandidates((prev) => prev.filter((c) => c.id !== candidateId))
      if (candidate) {
        info(`Candidate rule "${candidate.title}" dismissed.`, 'Rule Dismissed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject candidate')
    }
  }

  const approveAllHighConfidenceCandidates = () => {
    const highConf = pendingCandidates.filter((c) => c.confidence >= 90)
    highConf.forEach((c) => approveCandidateRule(c.id))
  }

  const uploadSourceDocument = async (newDoc: SourceDocument) => {
    setSourceDocuments((prev) => [newDoc, ...prev])

    // Generate simulated candidate rules into pending review queue in mock mode
    const generatedCandidates: PendingCandidateRule[] = [
      {
        id: `cand-${Date.now()}-1`,
        category: 'Claims & Restrictions',
        subCategory: 'Claims that require evidence',
        title: `Settlement Speed SLA (${newDoc.name})`,
        extractedText: 'Settlement commitments must cite audited clearing rails under 2026 scheme operating rules.',
        rationale: `Extracted from newly uploaded document ${newDoc.name}`,
        sourceDocument: newDoc.name,
        sourceSection: 'Page 3, Section 1.2',
        confidence: 96,
        dateExtracted: 'Just now',
        suggestedEnforcement: 'Strict',
      },
      {
        id: `cand-${Date.now()}-2`,
        category: 'Brand Voice',
        subCategory: 'Writing style',
        title: `Technical Precision Standard (${newDoc.name})`,
        extractedText: 'Quantify latency with P99 percentile distributions instead of qualitative claims.',
        rationale: `Extracted from newly uploaded document ${newDoc.name}`,
        sourceDocument: newDoc.name,
        sourceSection: 'Page 6, Section 2.1',
        confidence: 92,
        dateExtracted: 'Just now',
        suggestedEnforcement: 'Advisory',
      },
    ]

    setPendingCandidates((prev) => [...generatedCandidates, ...prev])
    success(`Document "${newDoc.name}" parsed! 2 new candidate rules queued for review.`, 'Document Extracted')
  }

  const uploadDocumentFile = async (file: File) => {
    setIsLoading(true)
    try {
      const brandId = currentWorkspace?.id
      const uploadedDoc = await guidelineService.uploadSourceDocument(file, brandId)
      // Refresh documents, pending candidates, and approved rules from backend
      const [candidatesData, docsData, rulesData] = await Promise.all([
        guidelineService.getPendingCandidates(brandId),
        guidelineService.getSourceDocuments(brandId),
        guidelineService.getApprovedRules(brandId),
      ])
      if (docsData && docsData.length > 0) {
        setSourceDocuments(docsData as unknown as SourceDocument[])
      } else {
        setSourceDocuments((prev) => [uploadedDoc as unknown as SourceDocument, ...prev])
      }
      if (candidatesData) {
        setPendingCandidates(candidatesData as unknown as PendingCandidateRule[])
      }
      if (rulesData) {
        setApprovedRules(rulesData as unknown as ApprovedRule[])
      }
      success(`Document "${file.name}" uploaded and parsed into brand knowledge queue!`, 'File Processed')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setError(msg)
      toastError(msg, 'Upload Failed')
    } finally {
      setIsLoading(false)
    }
  }

  const reExtractDocument = async (docId: string) => {
    setIsLoading(true)
    try {
      const brandId = currentWorkspace?.id
      const res = await guidelineService.reExtractDocument(docId, brandId)
      // Refresh documents, pending candidates, and approved rules from backend
      const [candidatesData, docsData, rulesData] = await Promise.all([
        guidelineService.getPendingCandidates(brandId),
        guidelineService.getSourceDocuments(brandId),
        guidelineService.getApprovedRules(brandId),
      ])
      if (docsData && docsData.length > 0) {
        setSourceDocuments(docsData as unknown as SourceDocument[])
      }
      if (candidatesData) {
        setPendingCandidates(candidatesData as unknown as PendingCandidateRule[])
      }
      if (rulesData) {
        setApprovedRules(rulesData as unknown as ApprovedRule[])
      }
      const count = res?.extractedCandidatesCount ?? 0
      success(`Rule extraction complete: ${count} candidate rules queued for review!`, 'Extraction Successful')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.detail || err?.message || 'Extraction failed'
      setError(msg)
      toastError(msg, 'Re-extraction Failed')
    } finally {
      setIsLoading(false)
    }
  }

  const deleteSourceDocument = async (docId: string) => {
    try {
      if (!apiClient.isMockMode()) {
        await apiClient.delete(`/api/v1/guidelines/${docId}`)
      }
      setSourceDocuments((prev) => prev.filter((d) => d.id !== docId))
      info('Source document removed from knowledge index.', 'Document Removed')
    } catch (err: any) {
      toastError(err?.detail || err?.message || 'Failed to delete document', 'Delete Failed')
    }
  }

  // Derived Telemetry
  const metrics = useMemo(() => {
    const pendingReviews = reviews.filter((r) => r.approvalStatus === 'pending' || r.approvalStatus === 'needs_revision' || r.approvalStatus === 'critical_issues').length
    const criticalIssues = telemetry?.criticalIssuesCount ?? reviews.reduce((sum, r) => sum + (r.findings?.filter(f => f.severity === 'critical').length || 0), 0)

    const hasReviews = reviews.length > 0 || (telemetry?.hasReviews ?? false)
    let avgScore = 100
    if (reviews.length > 0) {
      avgScore = Math.round(reviews.reduce((acc, r) => acc + (r.score || 0), 0) / reviews.length)
    } else if (telemetry && telemetry.hasReviews) {
      avgScore = telemetry.overallScore
    }

    return {
      overallScore: avgScore,
      hasReviews,
      contentReviewedCount: reviews.length,
      pendingApprovalsCount: pendingReviews,
      criticalIssuesCount: criticalIssues,
      approvedRulesCount: approvedRules.length,
      pendingCandidatesCount: pendingCandidates.length,
      sourceDocsCount: sourceDocuments.length,
      violationsByCategory: telemetry?.violationsByCategory || [],
      recentActivity: telemetry?.recentActivity || [],
    }
  }, [reviews, approvedRules, pendingCandidates, sourceDocuments, telemetry])

  return (
    <GovernanceContext.Provider
      value={{
        isLoading,
        error,
        refreshData,
        reviews,
        addReview,
        approveContent,
        requestChanges,
        addComment,
        approvedRules,
        pendingCandidates,
        sourceDocuments,
        addApprovedRule,
        updateApprovedRule,
        deleteApprovedRule,
        approveCandidateRule,
        rejectCandidateRule,
        approveAllHighConfidenceCandidates,
        uploadSourceDocument,
        uploadDocumentFile,
        reExtractDocument,
        deleteSourceDocument,
        metrics,
      }}
    >
      {children}
    </GovernanceContext.Provider>
  )
}

export const useGovernance = () => {
  const context = useContext(GovernanceContext)
  if (!context) {
    throw new Error('useGovernance must be used within a GovernanceProvider')
  }
  return context
}
