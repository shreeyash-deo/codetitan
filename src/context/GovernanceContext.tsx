import React, { createContext, useContext, useState, useEffect, useMemo } from 'react'
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
import { mockHistoricalReviews } from '@/data/mockHistoricalReviews'
import {
  initialApprovedRules,
  initialPendingCandidates,
  initialSourceDocuments,
} from '@/data/mockKnowledgeBase'
import { useToast } from './ToastContext'

interface GovernanceContextValue {
  // Loading & error state
  isLoading: boolean
  error: string | null

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
  deleteSourceDocument: (docId: string) => Promise<void>

  // Telemetry Metrics
  metrics: {
    overallScore: number
    contentReviewedCount: number
    pendingApprovalsCount: number
    criticalIssuesCount: number
    approvedRulesCount: number
    pendingCandidatesCount: number
    sourceDocsCount: number
  }
}

const GovernanceContext = createContext<GovernanceContextValue | undefined>(undefined)

export const GovernanceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { success, info, warning, error: toastError } = useToast()

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

  // Fetch initial data from services
  useEffect(() => {
    let isMounted = true

    const loadInitialData = async () => {
      if (apiClient.isMockMode()) return

      setIsLoading(true)
      setError(null)
      try {
        // Authenticate evaluator / default user
        await authService.getCurrentUser()

        const [rulesData, candidatesData, docsData, historyData] = await Promise.all([
          guidelineService.getApprovedRules(),
          guidelineService.getPendingCandidates(),
          guidelineService.getSourceDocuments(),
          historyService.getReviewHistory(),
        ])

        if (isMounted) {
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
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch live governance data from backend')
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadInitialData()
    return () => {
      isMounted = false
    }
  }, [])

  // Review Actions
  const addReview = (newReview: HistoricalReviewRecord) => {
    setReviews((prev) => [newReview, ...prev])
    info(`"${newReview.title}" added to the review queue.`, 'Review Ingested')
  }

  const approveContent = async (reviewId: string) => {
    const timestamp = 'Just now'

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

            const approvalComment = {
              id: `c-${Date.now()}`,
              authorName: 'Sarah Chen',
              authorRole: 'Brand Lead',
              authorAvatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
              text: 'Content explicitly verified and approved for publishing under brand guidelines.',
              timestamp,
            }

            return {
              ...r,
              approvalStatus: 'approved' as const,
              score: Math.max(r.score, 95),
              violationsCount: 0,
              comments: [...r.comments, approvalComment],
              timeline: updatedTimeline,
            }
          }
          return r
        })
      )

      success('Asset officially approved and certified for publication!', 'Approval Granted')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve asset')
    }
  }

  const requestChanges = async (reviewId: string, notes: string) => {
    const timestamp = 'Just now'

    try {
      if (!apiClient.isMockMode()) {
        await approvalService.requestChanges(reviewId, notes)
      }

      setReviews((prev) =>
        prev.map((r) => {
          if (r.id === reviewId) {
            const newComment = {
              id: `c-${Date.now()}`,
              authorName: 'Sarah Chen',
              authorRole: 'Brand Lead',
              authorAvatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit change request')
    }
  }

  const addComment = async (reviewId: string, commentText: string) => {
    const newComment = {
      id: `c-${Date.now()}`,
      authorName: 'Sarah Chen',
      authorRole: 'Brand Lead',
      authorAvatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add comment')
    }
  }

  // Guidelines Actions
  const addApprovedRule = async (rule: ApprovedRule) => {
    try {
      if (!apiClient.isMockMode()) {
        await guidelineService.createApprovedRule(rule as any)
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
      const uploadedDoc = await guidelineService.uploadSourceDocument(file)
      // Refresh documents and pending candidates from backend
      const [candidatesData, docsData] = await Promise.all([
        guidelineService.getPendingCandidates(),
        guidelineService.getSourceDocuments(),
      ])
      if (docsData && docsData.length > 0) {
        setSourceDocuments(docsData as unknown as SourceDocument[])
      } else {
        setSourceDocuments((prev) => [uploadedDoc as unknown as SourceDocument, ...prev])
      }
      if (candidatesData) {
        setPendingCandidates(candidatesData as unknown as PendingCandidateRule[])
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

  const deleteSourceDocument = async (docId: string) => {
    setSourceDocuments((prev) => prev.filter((d) => d.id !== docId))
    info('Source document removed from knowledge index.', 'Document Removed')
  }

  // Derived Telemetry
  const metrics = useMemo(() => {
    const pendingReviews = reviews.filter((r) => r.approvalStatus === 'pending' || r.approvalStatus === 'critical_issues').length
    const criticalIssues = reviews.filter((r) => r.approvalStatus === 'critical_issues').length

    let avgScore = 87
    if (!apiClient.isMockMode()) {
      avgScore = reviews.length > 0
        ? Math.round(reviews.reduce((acc, r) => acc + (r.score || 0), 0) / reviews.length)
        : 100
    }

    return {
      overallScore: avgScore,
      contentReviewedCount: apiClient.isMockMode() ? reviews.length + 119 : reviews.length,
      pendingApprovalsCount: pendingReviews,
      criticalIssuesCount: criticalIssues,
      approvedRulesCount: approvedRules.length,
      pendingCandidatesCount: pendingCandidates.length,
      sourceDocsCount: sourceDocuments.length,
    }
  }, [reviews, approvedRules, pendingCandidates, sourceDocuments])

  return (
    <GovernanceContext.Provider
      value={{
        isLoading,
        error,
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
