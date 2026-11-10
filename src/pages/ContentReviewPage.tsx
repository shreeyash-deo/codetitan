import React, { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useAuth } from '@/context/AuthContext'
import { useGovernance } from '@/context/GovernanceContext'
import { useToast } from '@/context/ToastContext'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { ContentSubmissionPanel } from '@/components/studio/ContentSubmissionPanel'
import { ReviewConfigPanel } from '@/components/studio/ReviewConfigPanel'
import { AnalysisProgressOverlay } from '@/components/studio/AnalysisProgressOverlay'
import { FindingCard } from '@/components/studio/FindingCard'
import { GuidelineInspectorDrawer } from '@/components/studio/GuidelineInspectorDrawer'
import { CompareDiffModal } from '@/components/studio/CompareDiffModal'
import { ExportReportModal } from '@/components/studio/ExportReportModal'
import { studioPresets } from '@/data/mockStudioPresets'
import { reviewService, apiClient } from '@/services'
import type { HistoricalReviewRecord } from '@/types/approval'
import type {
  StudioContentType,
  StudioCategory,
  StrictnessLevel,
  StudioFinding,
  SupportingGuideline,
} from '@/types/reviewStudio'
import {
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  FileCheck2,
  GitCompare,
  Download,
  Send,
  Save,
  RotateCcw,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Edit3,
  Eye,
} from 'lucide-react'

export const ContentReviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { currentWorkspace } = useWorkspace()
  const { approvedRules, sourceDocuments, addReview, refreshData, isLoading: isLoadingGovernance } = useGovernance()
  const { success, warning, info, error: toastError } = useToast()

  // Clean, non-prepopulated editor state
  const [title, setTitle] = useState('')
  const [contentType, setContentType] = useState<StudioContentType>('Social media')
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  // Real API integration state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeReviewId, setActiveReviewId] = useState<string | null>(null)
  const [realBackendScore, setRealBackendScore] = useState<number | null>(null)
  const [realSummary, setRealSummary] = useState<string | null>(null)
  const [lastAuditedContent, setLastAuditedContent] = useState<string | null>(null)

  // Configuration options
  const [strictness, setStrictness] = useState<StrictnessLevel>('standard')
  const [activeCategories, setActiveCategories] = useState<StudioCategory[]>([
    'Tone inconsistency',
    'Incorrect terminology',
    'Unsupported claims',
    'Incorrect product facts',
    'Visual brand inconsistency',
  ])
  const [activeGuidelines, setActiveGuidelines] = useState<string[]>([])

  // Studio Flow State: 'idle' | 'analyzing' | 'results'
  const [studioState, setStudioState] = useState<'idle' | 'analyzing' | 'results'>('idle')
  const [findings, setFindings] = useState<StudioFinding[]>([])
  const [selectedGuideline, setSelectedGuideline] = useState<SupportingGuideline | null>(null)
  const [isGuidelineDrawerOpen, setIsGuidelineDrawerOpen] = useState(false)
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false)
  const [isExportModalOpen, setIsExportModalOpen] = useState(false)
  const [selectedFilterCategory, setSelectedFilterCategory] = useState<string>('all')
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null)
  const [isDirectEditing, setIsDirectEditing] = useState(false)

  // Real linked guidelines derived strictly from the active organization's approved knowledge base
  const linkedGuidelines = useMemo(() => {
    if (sourceDocuments && sourceDocuments.length > 0) {
      return sourceDocuments.map((doc) => ({
        id: `doc-${doc.id}`,
        name: doc.name,
        count: doc.approvedRulesCount || 0,
        desc: `${doc.format || 'Document'} guideline source`,
      }))
    }
    if (approvedRules && approvedRules.length > 0) {
      const categoryMap = new Map<string, number>()
      for (const r of approvedRules) {
        const cat = r.category || 'General'
        categoryMap.set(cat, (categoryMap.get(cat) || 0) + 1)
      }
      return Array.from(categoryMap.entries()).map(([cat, count]) => ({
        id: `cat-${cat.toLowerCase().replace(/\s+/g, '-')}`,
        name: cat,
        count,
        desc: 'Official active ruleset',
      }))
    }
    return []
  }, [sourceDocuments, approvedRules])

  // Ensure latest approved rules & telemetry are loaded for current workspace
  useEffect(() => {
    refreshData()
  }, [currentWorkspace?.id, refreshData])

  // Load Preset
  const handleSelectPreset = (presetId: string) => {
    const found = studioPresets.find(p => p.id === presetId)
    if (found) {
      setTitle(found.title)
      setContentType(found.contentType)
      setContent(found.rawContent)
      setOriginalContent(found.rawContent)
      setFindings(found.findings.map(f => ({ ...f, status: 'pending' })))
      setSelectedFile(null)
      setStudioState('idle')
      info(`Loaded benchmark preset: "${found.title}".`, 'Preset Loaded')
    }
  }

  const mapBackendFindings = (rawFindings: any[]): StudioFinding[] => {
    return (rawFindings || []).map((f) => {
      const origText = f.originalText || f.excerpt || f.snippet || ''
      const explanation = f.explanation || ''
      const guidelineRef = f.guideline_reference || f.supportingGuidelineTitle || ''
      const code = f.supportingGuidelineCode || (guidelineRef.includes(':') ? guidelineRef.split(':')[0].trim() : 'RULE')
      const title = f.supportingGuidelineTitle || (guidelineRef.includes(':') ? guidelineRef.split(':', 2)[1].trim() : guidelineRef) || explanation
      const correction = f.suggestedCorrection || f.suggested_correction || f.suggestion || ''
      const conf = f.confidence !== undefined ? (f.confidence <= 1.0 ? Math.round(f.confidence * 100) : Math.round(f.confidence)) : 90
      const isResolved = f.resolved || f.status === 'accepted' || f.status === 'applied'

      return {
        id: String(f.id),
        category: (f.category as StudioCategory) || 'Unsupported claims',
        severity: f.severity === 'critical' ? 'critical' : (f.severity === 'major' || f.severity === 'moderate' ? 'warning' : 'info'),
        originalText: origText,
        explanation,
        supportingGuideline: {
          id: `g-${f.id}`,
          code,
          category: f.category,
          title,
          description: explanation,
          rationale: explanation,
          enforcementLevel: f.severity === 'critical' ? 'Strict' : 'Advisory',
        },
        suggestedCorrection: correction,
        confidence: conf,
        status: isResolved ? 'accepted' : (f.status === 'rejected' ? 'rejected' : 'pending'),
      }
    })
  }

  // Run Brand Review / Recheck
  const handleRunReview = async () => {
    if (!content.trim()) return
    // Preserve immutable original submission on first run; do not overwrite on recheck
    if (!originalContent) {
      setOriginalContent(content)
    }

    if (apiClient.isMockMode()) {
      setStudioState('analyzing')
      return
    }

    setIsSubmitting(true)
    try {
      if (activeReviewId) {
        // If content was modified, update review and re-audit via PATCH
        const res: any = await apiClient.patch(`/api/v1/reviews/${activeReviewId}`, {
          title: title.trim() || 'Marketing Asset',
          content: content.trim(),
        })
        const data = res?.data ?? res
        setRealBackendScore(data.compliance_score)
        setRealSummary(data.summary)
        const newContent = data?.content ?? data?.updated_content ?? content.trim()
        setLastAuditedContent(newContent)

        if (data.audit_status === 'rules_unavailable') {
          setFindings([])
          setStudioState('results')
          warning(data.summary || 'Brand rules unavailable in this organisation.', 'Incomplete Audit')
          return
        }

        setFindings(mapBackendFindings(data.findings || []))
        setStudioState('results')
        success(`Recheck completed. Verified compliance score: ${data.compliance_score}/100.`, 'Analysis Verified')
        return
      }

      const channel = contentType === 'Blog' ? 'Blog' : (contentType === 'Advertisement' ? 'Ad Creative' : 'Social')
      const result = await reviewService.submitContentForReview({
        title: title.trim() || 'Marketing Asset',
        content: content.trim(),
        contentType,
        channel,
        strictness,
        activeCategories,
      }, currentWorkspace?.id)

      setActiveReviewId(result.id)
      setRealBackendScore(result.overallScore)
      setRealSummary(result.summary)
      setLastAuditedContent(content.trim())

      if (result.status === 'rules_unavailable' || result.hasApprovedRules === false) {
        setFindings([])
        setStudioState('results')
        warning(
          result.summary || 'Brand rules unavailable in this organisation. Please approve brand rules before auditing.',
          'Incomplete Audit'
        )
        return
      }

      setFindings(mapBackendFindings(result.findings || []))
      setStudioState('results')
      success(`Compliance analysis completed. Compliance score: ${result.overallScore}/100.`, 'Analysis Complete')
    } catch (err: any) {
      const msg = err?.detail || err?.message || 'Compliance analysis failed'
      toastError(msg, 'Audit Notice')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Analysis Complete Callback (for mock mode timer)
  const handleAnalysisComplete = () => {
    setStudioState('results')
    info('Governance scan completed against active guidelines.', 'Audit Finished')
  }

  // Finding correction actions
  const handleAcceptSuggestion = async (findingId: string) => {
    const target = findings.find(f => f.id === findingId)
    if (!target) return

    if (!apiClient.isMockMode() && activeReviewId) {
      try {
        const res: any = await apiClient.post(`/api/v1/reviews/${activeReviewId}/findings/${findingId}/apply`)
        const data = res?.data ?? res
        const newContent = data?.content ?? data?.updated_content ?? content
        setContent(newContent)
        setRealBackendScore(data.compliance_score)
        setLastAuditedContent(newContent)
        if (data.findings) {
          setFindings(mapBackendFindings(data.findings))
        }
        success(`Correction applied for "${target.category}". Verified score: ${data.compliance_score}/100.`, 'Correction Applied')
        return
      } catch (err: any) {
        toastError(
          err?.response?.data?.detail || err?.detail || err?.message || 'Failed to apply correction on server',
          'Replacement Failed'
        )
        return
      }
    }

    const replacement = target.manualReplacement || target.suggestedCorrection || ''
    const orig = target.originalText

    let wasModified = false
    let failureDetail = ''

    setContent(prev => {
      if (orig === '[Missing Regulatory Disclaimer]' || replacement.startsWith('\n\nDisclaimer:')) {
        const toAppend = replacement.startsWith('\n\n') ? replacement : '\n\n' + replacement
        const cleanDisc = replacement.replace('\n\nDisclaimer:', '').trim().toLowerCase()
        const cleanPrev = prev.toLowerCase()

        if (cleanPrev.includes('disclaimer:') || (cleanDisc && cleanPrev.includes(cleanDisc))) {
          wasModified = true
          return prev
        }
        wasModified = true
        return prev.trimEnd() + toAppend
      }

      if (orig && prev.includes(orig)) {
        wasModified = true
        return prev.replace(orig, replacement)
      }

      if (orig) {
        const escaped = orig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        const regex = new RegExp(escaped, 'i')
        if (regex.test(prev)) {
          wasModified = true
          return prev.replace(regex, replacement)
        }
      }

      failureDetail = `Could not locate "${orig}" in working copy. It may have been altered by another edit.`
      return prev
    })

    if (!wasModified) {
      toastError(
        failureDetail || `Cannot apply fix: offending text was not found in working copy.`,
        'Replacement Failed'
      )
      return
    }

    setFindings(prev =>
      prev.map(f => (f.id === findingId ? { ...f, status: 'accepted' } : f))
    )

    success(`Accepted correction for "${target.category}". Click 'Recheck Content' to re-verify compliance.`, 'Correction Applied')
  }

  // Batch Accept All Suggestions cleanly without toast loops or state corruption
  const handleAcceptAllSuggestions = async () => {
    const pendingToApply = findings.filter(f => f.status === 'pending')
    if (pendingToApply.length === 0) return

    if (!apiClient.isMockMode() && activeReviewId) {
      setIsSubmitting(true)
      try {
        const res: any = await apiClient.post(`/api/v1/reviews/${activeReviewId}/findings/batch-apply`)
        const data = res?.data ?? res
        const newContent = data?.content ?? data?.updated_content ?? content
        setContent(newContent)
        setRealBackendScore(data.compliance_score)
        setLastAuditedContent(newContent)
        if (data.findings) {
          setFindings(mapBackendFindings(data.findings))
        }
        success(`All suggestions applied and verified. New compliance score: ${data.compliance_score}/100.`, 'Batch Applied & Verified')
        return
      } catch (err: any) {
        toastError(
          err?.response?.data?.detail || err?.detail || err?.message || 'Batch correction failed on server',
          'Application Failed'
        )
        return
      } finally {
        setIsSubmitting(false)
      }
    }

    let appliedCount = 0
    let failedCount = 0
    const appliedIds = new Set<string>()

    setContent(prev => {
      let updated = prev
      let disclaimerToAppend = ''

      for (const f of pendingToApply) {
        const repl = f.manualReplacement || f.suggestedCorrection || ''
        const orig = f.originalText

        if (orig === '[Missing Regulatory Disclaimer]' || repl.startsWith('\n\nDisclaimer:')) {
          const toAppend = repl.startsWith('\n\n') ? repl : '\n\n' + repl
          const cleanDisc = repl.replace('\n\nDisclaimer:', '').trim().toLowerCase()
          const cleanPrev = updated.toLowerCase()

          if (!cleanPrev.includes('disclaimer:') && (!cleanDisc || !cleanPrev.includes(cleanDisc))) {
            disclaimerToAppend = toAppend
          }
          appliedCount++
          appliedIds.add(f.id)
        } else if (orig && updated.includes(orig)) {
          updated = updated.replace(orig, repl)
          appliedCount++
          appliedIds.add(f.id)
        } else if (orig) {
          const escaped = orig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
          const regex = new RegExp(escaped, 'i')
          if (regex.test(updated)) {
            updated = updated.replace(regex, repl)
            appliedCount++
            appliedIds.add(f.id)
          } else {
            failedCount++
          }
        } else {
          failedCount++
        }
      }

      if (disclaimerToAppend) {
        updated = updated.trimEnd() + disclaimerToAppend
      }
      return updated
    })

    setFindings(prev =>
      prev.map(f => (appliedIds.has(f.id) ? { ...f, status: 'accepted' } : f))
    )

    if (appliedCount > 0 && failedCount === 0) {
      success(`Applied ${appliedCount} corrections to draft. Click 'Recheck Content' to verify score.`, 'Corrections Applied')
    } else if (appliedCount > 0 && failedCount > 0) {
      warning(`Applied ${appliedCount} corrections. ${failedCount} suggestion(s) could not be located in working text.`, 'Partial Application')
    } else {
      toastError('Could not match pending suggestions in current working draft.', 'Application Failed')
    }
  }

  const handleRejectSuggestion = (findingId: string) => {
    setFindings(prev =>
      prev.map(f => (f.id === findingId ? { ...f, status: 'rejected' } : f))
    )
    info('Suggestion dismissed by reviewer.', 'Dismissed')
  }

  const handleManualEdit = (findingId: string, customReplacement: string) => {
    const target = findings.find(f => f.id === findingId)
    if (!target) return

    let wasModified = false
    setContent(prev => {
      if (prev.includes(target.originalText)) {
        wasModified = true
        return prev.replace(target.originalText, customReplacement)
      }
      const escaped = target.originalText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const regex = new RegExp(escaped, 'i')
      if (regex.test(prev)) {
        wasModified = true
        return prev.replace(regex, customReplacement)
      }
      return prev
    })

    if (!wasModified) {
      toastError(`Could not locate "${target.originalText}" in working draft to replace.`, 'Manual Edit Failed')
      return
    }

    setFindings(prev =>
      prev.map(f =>
        f.id === findingId
          ? { ...f, status: 'manual', manualReplacement: customReplacement }
          : f
      )
    )

    success('Custom correction applied to working document. Click \'Recheck Content\' to re-verify compliance.', 'Custom Text Applied')
  }

  const handleViewGuideline = (finding: StudioFinding) => {
    setSelectedGuideline(finding.supportingGuideline)
    setIsGuidelineDrawerOpen(true)
  }

  // Calculate dynamic counts based on findings
  const totalFindings = findings.length
  const acceptedCount = findings.filter(f => f.status === 'accepted' || f.status === 'manual').length
  const rejectedCount = findings.filter(f => f.status === 'rejected').length
  const pendingCount = findings.filter(f => f.status === 'pending').length

  // Authoritative rules availability:
  // In results mode, use the backend audit verdict (never false-flag if findings exist).
  // In idle mode, check whether the workspace has approved guidelines loaded.
  const isRulesUnavailable = studioState === 'results'
    ? Boolean(realSummary && realSummary.toLowerCase().includes('rules unavailable'))
    : (!isLoadingGovernance && approvedRules !== undefined && approvedRules.length === 0)

  // Authoritative compliance score is determined strictly by verified audit results
  // Never calculate score from accepted suggestion count or award 100/100 while violations remain
  const verifiedScore = isRulesUnavailable
    ? 0
    : (realBackendScore !== null ? realBackendScore : (totalFindings === 0 ? 100 : 0))
  const currentScore = verifiedScore

  const isDraftModified = studioState === 'results' && lastAuditedContent !== null && content.trim() !== lastAuditedContent

  // Severity counts
  const criticalCount = findings.filter(f => f.severity === 'critical' && f.status === 'pending').length
  const warningCount = findings.filter(f => f.severity === 'warning' && f.status === 'pending').length
  const infoCount = findings.filter(f => f.severity === 'info' && f.status === 'pending').length

  // Filtered findings list
  const filteredFindings = findings.filter(f => {
    if (selectedFilterCategory === 'all') return true
    if (selectedFilterCategory === 'pending') return f.status === 'pending'
    if (selectedFilterCategory === 'accepted') return f.status === 'accepted' || f.status === 'manual'
    return f.category.toLowerCase() === selectedFilterCategory.toLowerCase()
  })

  // Final actions
  const handleSaveReview = async () => {
    if (!apiClient.isMockMode() && activeReviewId) {
      setIsSubmitting(true)
      try {
        const res: any = await apiClient.patch(`/api/v1/reviews/${activeReviewId}`, {
          title: title.trim() || 'Marketing Asset',
          content: content.trim(),
        })
        const data = res?.data ?? res
        setRealBackendScore(data.compliance_score)
        const newContent = data?.content ?? data?.updated_content ?? content.trim()
        setLastAuditedContent(newContent)
        if (data.findings) {
          setFindings(mapBackendFindings(data.findings))
        }
        success(`Review for "${title}" saved and verified by compliance engine. Score: ${data.compliance_score}/100.`, 'Review Saved & Verified')
      } catch (err: any) {
        toastError(err?.response?.data?.detail || err?.detail || err?.message || 'Failed to save review', 'Save Failed')
      } finally {
        setIsSubmitting(false)
      }
    } else {
      success(`Review for "${title}" saved to local governance records.`, 'Review Saved')
    }
  }

  const handleSubmitForApproval = async () => {
    if (criticalCount > 0) {
      warning(
        `Cannot submit for approval with ${criticalCount} unresolved critical violations. Please accept suggestions or edit manually first.`,
        'Approval Blocked'
      )
      return
    }

    if (isDraftModified) {
      warning(
        'Working draft has unverified modifications. Please click "Recheck Content" or "Save Review" to re-verify compliance before requesting approval.',
        'Recheck Required'
      )
      return
    }

    let reviewIdToSubmit = activeReviewId

    if (!apiClient.isMockMode()) {
      try {
        if (!reviewIdToSubmit) {
          const channel = contentType === 'Blog' ? 'Blog' : (contentType === 'Advertisement' ? 'Ad Creative' : 'Social')
          const result = await reviewService.submitContentForReview({
            title: title.trim() || 'Marketing Asset',
            content: content.trim(),
            contentType,
            channel,
            strictness,
            activeCategories,
          }, currentWorkspace?.id)
          reviewIdToSubmit = result.id
          setActiveReviewId(result.id)
        } else if (content !== lastAuditedContent) {
          const saveRes: any = await apiClient.patch(`/api/v1/reviews/${reviewIdToSubmit}`, {
            content: content,
          })
          const saveData = saveRes?.data ?? saveRes
          const savedContent = saveData?.content ?? saveData?.updated_content ?? content
          setLastAuditedContent(savedContent)
          setRealBackendScore(saveData.compliance_score)
        }

        if (reviewIdToSubmit) {
          await apiClient.post(`/api/v1/reviews/${reviewIdToSubmit}/request-approval`, {
            summary: `Submitted for sign-off with ${acceptedCount} corrections applied. Current compliance score: ${currentScore}%.`,
          })
        }
      } catch (err: any) {
        const errorDetail = err?.response?.data?.detail || err?.detail || err?.message || 'Approval request failed'
        toastError(errorDetail, 'Submission Notice')
        return
      }
    }

    const authorName = user?.name || 'Author'
    const authorRole = currentWorkspace?.role || 'Employee'
    const authorEmail = user?.email || 'author@brandshield.local'

    // Create full HistoricalReviewRecord and dispatch to GovernanceContext!
    const newApprovalRecord: HistoricalReviewRecord = {
      id: reviewIdToSubmit || `rev-sub-${Date.now().toString().slice(-4)}`,
      title: title.trim() || 'Marketing Collateral',
      contentType: `${contentType} Collateral`,
      channel: contentType === 'Blog' ? 'Blog' : (contentType === 'Advertisement' ? 'Ad Creative' : 'Social'),
      submittedBy: {
        name: authorName,
        role: authorRole,
        email: authorEmail,
        avatar: `https://api.dicebear.com/7.x/initials/svg?seed=${authorName}`,
      },
      assignedReviewer: {
        name: 'Designated Reviewer',
        role: 'Reviewer',
        email: 'reviewer@brandshield.local',
        avatar: 'https://api.dicebear.com/7.x/initials/svg?seed=Reviewer',
      },
      score: currentScore,
      violationsCount: pendingCount,
      reviewDate: 'Today',
      approvalStatus: 'pending',
      originalContent,
      correctedContent: content,
      findings: findings.map(f => ({
        id: f.id,
        category: f.category as any,
        severity: f.severity === 'info' ? 'minor' : (f.severity === 'warning' ? 'moderate' : 'critical'),
        snippet: f.originalText,
        explanation: f.explanation,
        suggestion: f.suggestedCorrection,
        resolved: f.status === 'accepted' || f.status === 'manual',
      })),
      acceptedSuggestionsCount: acceptedCount,
      rejectedSuggestionsCount: rejectedCount,
      comments: [],
      timeline: [
        {
          id: `t-${Date.now()}-1`,
          stage: 'Content submitted',
          actorName: authorName,
          actorRole: authorRole,
          timestamp: 'Just now',
          note: `Submission summary: ${acceptedCount} corrections applied. Current compliance score: ${currentScore}%.`,
          status: 'completed',
        },
        {
          id: `t-${Date.now()}-2`,
          stage: 'AI review completed',
          actorName: 'BrandShield AI',
          actorRole: 'Automated Sentinel',
          timestamp: 'Just now',
          note: `Initial audit score: ${currentScore}/100.`,
          status: 'completed',
        },
        {
          id: `t-${Date.now()}-3`,
          stage: 'Suggestions applied',
          actorName: authorName,
          actorRole: 'Author',
          timestamp: 'Just now',
          note: `${acceptedCount} suggestions accepted in studio.`,
          status: 'completed',
        },
        {
          id: `t-${Date.now()}-4`,
          stage: 'Approval requested',
          actorName: authorName,
          actorRole: 'Author',
          timestamp: 'Just now',
          note: 'Assigned for compliance verification.',
          status: 'completed',
        },
        {
          id: `t-${Date.now()}-5`,
          stage: 'Reviewer decision',
          actorName: 'Designated Reviewer',
          actorRole: 'Reviewer',
          timestamp: 'Pending',
          status: 'current',
        },
      ],
    }

    addReview(newApprovalRecord)
    if (!apiClient.isMockMode()) {
      refreshData()
    }
    success(`"${title}" successfully routed to Team & Approvals queue!`, 'Routed for Approval')
    navigate('/team-approvals')
  }

  // Interactive Highlighting Renderer for Document View
  const renderHighlightedContent = () => {
    if (!content) return <span className="text-slate-400 italic">No content</span>

    interface Match {
      start: number
      end: number
      finding: StudioFinding
    }
    const matches: Match[] = []

    findings.forEach((f) => {
      if (!f.originalText || f.originalText.trim().length === 0) return
      let pos = 0
      while (pos < content.length) {
        const idx = content.indexOf(f.originalText, pos)
        if (idx === -1) break
        matches.push({
          start: idx,
          end: idx + f.originalText.length,
          finding: f,
        })
        pos = idx + f.originalText.length
      }
    })

    matches.sort((a, b) => a.start - b.start)

    const filteredMatches: Match[] = []
    let lastEnd = 0
    for (const m of matches) {
      if (m.start >= lastEnd) {
        filteredMatches.push(m)
        lastEnd = m.end
      }
    }

    if (filteredMatches.length === 0) {
      return <span className="whitespace-pre-wrap">{content}</span>
    }

    const elements: React.ReactNode[] = []
    let cursor = 0

    filteredMatches.forEach((m, i) => {
      if (m.start > cursor) {
        elements.push(
          <span key={`text-${cursor}`}>{content.slice(cursor, m.start)}</span>
        )
      }

      const isSelected = selectedFindingId === m.finding.id
      const isResolved = m.finding.status === 'accepted' || m.finding.status === 'manual'
      const isCritical = m.finding.severity === 'critical'

      elements.push(
        <mark
          key={`match-${i}-${m.start}`}
          onClick={(e) => {
            e.stopPropagation()
            setSelectedFindingId(m.finding.id)
          }}
          className={`px-1 py-0.5 rounded cursor-pointer transition-all ${
            isSelected
              ? 'bg-amber-300 text-amber-950 font-semibold ring-2 ring-blue-500 shadow-sm'
              : isResolved
              ? 'bg-emerald-100 text-emerald-900 border border-emerald-300 line-through opacity-70'
              : isCritical
              ? 'bg-rose-100 text-rose-900 border border-rose-300 hover:bg-rose-200'
              : 'bg-amber-100 text-amber-900 border border-amber-200 hover:bg-amber-200'
          }`}
          title={`Click to focus: ${m.finding.category} - ${m.finding.explanation}`}
        >
          {content.slice(m.start, m.end)}
        </mark>
      )

      cursor = m.end
    })

    if (cursor < content.length) {
      elements.push(
        <span key={`text-${cursor}`}>{content.slice(cursor)}</span>
      )
    }

    return <span className="whitespace-pre-wrap">{elements}</span>
  }

  const selectedFinding = findings.find(f => f.id === selectedFindingId)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      {/* Page Header */}
      <PageHeader
        title="Content Review Studio"
        description="Verify marketing collateral, product blogs, ad creative, and landing pages against approved brand guidelines."
        badge={
          <Badge variant="blue" className="gap-1 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            AI Studio v2.4
          </Badge>
        }
        actions={
          studioState === 'results' ? (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-blue-700 border-blue-200 hover:bg-blue-50"
                onClick={handleRunReview}
                disabled={isSubmitting}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSubmitting ? 'animate-spin' : ''}`} />
                <span>Recheck Content</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => setIsCompareModalOpen(true)}
              >
                <GitCompare className="w-3.5 h-3.5 text-slate-600" />
                <span>Compare Versions</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => setIsExportModalOpen(true)}
              >
                <Download className="w-3.5 h-3.5 text-slate-600" />
                <span>Export Report</span>
              </Button>

              <Button
                variant="primaryBlue"
                size="sm"
                className="gap-1.5"
                onClick={handleSubmitForApproval}
              >
                <Send className="w-3.5 h-3.5" />
                <span>Submit for Approval</span>
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {content && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setTitle('')
                    setContent('')
                    setOriginalContent('')
                    setFindings([])
                    setSelectedFile(null)
                  }}
                  className="text-xs"
                >
                  Clear Draft
                </Button>
              )}
            </div>
          )
        }
      />

      {/* STUDIO MODE 1: SUBMISSION & CONFIGURATION */}
      {studioState === 'idle' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7">
            <ContentSubmissionPanel
              title={title}
              setTitle={setTitle}
              contentType={contentType}
              setContentType={setContentType}
              content={content}
              setContent={setContent}
              workspaceName={currentWorkspace?.name || 'Organisation'}
              onRunReview={handleRunReview}
              isAnalyzing={isSubmitting}
              onSelectPreset={handleSelectPreset}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile}
            />
          </div>

          <div className="lg:col-span-5">
            <ReviewConfigPanel
              activeCategories={activeCategories}
              toggleCategory={(cat) => {
                setActiveCategories(prev =>
                  prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
                )
              }}
              strictness={strictness}
              setStrictness={setStrictness}
              activeGuidelines={activeGuidelines}
              toggleGuideline={(id) => {
                setActiveGuidelines(prev =>
                  prev.includes(id) ? prev.filter(g => g !== id) : [...prev, id]
                )
              }}
              contentLength={content.length}
              wordCount={content.trim() ? content.trim().split(/\s+/).length : 0}
              status="ready"
              linkedGuidelines={linkedGuidelines}
              totalRulesCount={approvedRules?.length || 0}
              isLoadingGuidelines={isLoadingGovernance}
            />
          </div>
        </div>
      )}

      {/* STUDIO MODE 2: COMPLIANCE RESULTS DASHBOARD */}
      {studioState === 'results' && (
        <div className="space-y-6">
          {/* Top Score Bar */}
          <div className="p-5 rounded-xl bg-slate-900 text-white shadow-xs border border-slate-800">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="blue" className="text-[10px] font-mono">
                    {contentType}
                  </Badge>
                  <span className="text-xs text-slate-400">
                    Audit complete for {currentWorkspace?.name || 'Organisation'}
                  </span>
                </div>
                <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white">
                  {title}
                </h2>
                <p className="text-xs text-slate-300">
                  {isRulesUnavailable
                    ? 'Brand rules unavailable. Please approve brand rules in Brand Guidelines to run compliance audits.'
                    : (isDraftModified
                        ? `Draft modified with ${acceptedCount} correction(s). Click "Recheck Content" to re-verify compliance score.`
                        : (totalFindings > 0
                            ? `${findings.length} findings identified. Remediate and recheck before publication.`
                            : 'All brand compliance checks verified. Content ready for publication.'))}
                </p>
              </div>

              {/* Score Display & Metric Pills */}
              <div className="flex items-center gap-4 shrink-0">
                <div className="flex flex-col bg-slate-950/60 border border-white/10 rounded-lg p-3 text-center min-w-[90px]">
                  <span className={`text-2xl font-extrabold ${isRulesUnavailable ? 'text-amber-400' : (currentScore >= 90 ? 'text-emerald-400' : 'text-blue-400')}`}>
                    {isRulesUnavailable ? 'N/A' : currentScore}
                    {!isRulesUnavailable && <span className="text-xs text-slate-400 font-normal">/100</span>}
                  </span>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                    {isRulesUnavailable ? 'Incomplete' : (isDraftModified ? 'Unverified' : 'Verified Score')}
                  </span>
                </div>

                <div className="flex flex-col gap-1.5 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-300 bg-rose-950/60 border border-rose-800/80 px-2 py-0.5 rounded">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                      {criticalCount} Critical
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-300 bg-amber-950/60 border border-amber-800/80 px-2 py-0.5 rounded">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                      {warningCount} Warnings
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-300 bg-blue-950/60 border border-blue-800/80 px-2 py-0.5 rounded">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      {infoCount} Info
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {acceptedCount} of {totalFindings} corrections accepted
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Working Copy vs Findings List */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 space-y-4">
              <Card className="h-full border-border flex flex-col justify-between">
                <CardHeader className="pb-3 border-b border-border/70">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                        <FileCheck2 className="w-4 h-4 text-blue-600" />
                        <span>Working Document Copy</span>
                      </CardTitle>
                      <CardDescription className="text-xs text-slate-500">
                        Updates live as you accept suggestions or edit manually
                      </CardDescription>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <div className="flex items-center bg-slate-100 p-0.5 rounded-md text-[11px]">
                        <button
                          type="button"
                          onClick={() => setIsDirectEditing(false)}
                          className={`px-2 py-0.5 rounded flex items-center gap-1 transition-all ${
                            !isDirectEditing ? 'bg-white text-slate-900 font-semibold shadow-2xs' : 'text-slate-500 hover:text-slate-900'
                          }`}
                        >
                          <Eye className="w-3 h-3 text-blue-600" />
                          <span>Inspect</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setIsDirectEditing(true)}
                          className={`px-2 py-0.5 rounded flex items-center gap-1 transition-all ${
                            isDirectEditing ? 'bg-white text-slate-900 font-semibold shadow-2xs' : 'text-slate-500 hover:text-slate-900'
                          }`}
                        >
                          <Edit3 className="w-3 h-3 text-slate-600" />
                          <span>Edit</span>
                        </button>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-[11px] gap-1"
                        onClick={() => setIsCompareModalOpen(true)}
                      >
                        <GitCompare className="w-3 h-3" />
                        <span>Compare Diff</span>
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-4 space-y-3 flex-1 flex flex-col">
                  {selectedFinding && selectedFinding.status === 'pending' && (
                    <div className="p-2.5 rounded-lg bg-blue-50/90 border border-blue-200 flex items-center justify-between gap-2 text-xs">
                      <div className="min-w-0">
                        <div className="font-semibold text-blue-900 truncate flex items-center gap-1.5">
                          <Sparkles className="w-3 h-3 text-blue-600 shrink-0" />
                          <span>Focused Violation: {selectedFinding.category}</span>
                        </div>
                        <div className="text-[11px] text-slate-600 truncate mt-0.5">
                          <span className="line-through text-rose-600">"{selectedFinding.originalText}"</span> → <strong className="text-emerald-700 font-semibold">"{selectedFinding.suggestedCorrection}"</strong>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="primaryBlue"
                        className="h-7 text-xs font-semibold shrink-0 gap-1"
                        onClick={() => handleAcceptSuggestion(selectedFinding.id)}
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Apply Fix</span>
                      </Button>
                    </div>
                  )}

                  {!isDirectEditing ? (
                    <div className="flex-1 p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-serif leading-relaxed text-slate-800 min-h-[360px] whitespace-pre-wrap select-text">
                      {renderHighlightedContent()}
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col space-y-2 min-h-[360px]">
                      <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        className="flex-1 w-full p-3.5 rounded-lg bg-white border border-slate-300 text-xs font-mono leading-relaxed text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-inner resize-none min-h-[340px]"
                        placeholder="Edit draft text directly..."
                      />
                      <p className="text-[10px] text-slate-400">
                        Manual edits persist across re-checks and will be scanned against brand rules.
                      </p>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                    <span>{content.length} characters • {content.trim().split(/\s+/).length} words</span>
                    <button
                      onClick={() => {
                        setContent(originalContent)
                        setFindings(prev => prev.map(f => ({ ...f, status: 'pending' })))
                        info('Reverted working document to original draft.', 'Reset Draft')
                      }}
                      className="text-slate-500 hover:text-slate-800 flex items-center gap-1"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Reset to Original</span>
                    </button>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-7 space-y-4">
              {/* Filter Tabs */}
              <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-border shadow-xs">
                <div className="flex items-center gap-1 overflow-x-auto">
                  {[
                    { id: 'all', label: 'All Findings', count: findings.length },
                    { id: 'pending', label: 'Pending', count: pendingCount },
                    { id: 'accepted', label: 'Accepted', count: acceptedCount },
                    { id: 'unsupported claims', label: 'Claims', count: findings.filter(f => f.category === 'Unsupported claims').length },
                    { id: 'tone inconsistency', label: 'Tone', count: findings.filter(f => f.category === 'Tone inconsistency').length },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setSelectedFilterCategory(tab.id)}
                      className={`px-2.5 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0 ${
                        selectedFilterCategory === tab.id
                          ? 'bg-slate-900 text-white'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <span>{tab.label}</span>
                      <span className={`text-[10px] px-1 rounded-full ${selectedFilterCategory === tab.id ? 'bg-slate-700' : 'bg-slate-200'}`}>
                        {tab.count}
                      </span>
                    </button>
                  ))}
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-7 text-blue-600 hover:text-blue-800"
                  onClick={handleAcceptAllSuggestions}
                  disabled={pendingCount === 0}
                >
                  Accept All ({pendingCount})
                </Button>
              </div>

              {/* Findings Cards List */}
              <div className="space-y-3">
                {filteredFindings.map((finding) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    isSelected={selectedFindingId === finding.id}
                    onSelect={(id) => setSelectedFindingId(id)}
                    onAccept={handleAcceptSuggestion}
                    onReject={handleRejectSuggestion}
                    onManualEdit={handleManualEdit}
                    onViewGuideline={handleViewGuideline}
                  />
                ))}
              </div>

              {/* Bottom Sticky Action Bar */}
              <div className="p-4 rounded-xl bg-white border border-border shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="text-xs text-slate-500">
                  {criticalCount === 0 ? (
                    <span className="text-emerald-700 font-medium flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      All critical compliance blockers resolved!
                    </span>
                  ) : (
                    <span className="text-amber-700 font-medium flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      {criticalCount} critical issue(s) remaining before publishing.
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-blue-700 border-blue-200 hover:bg-blue-50"
                    onClick={handleRunReview}
                    disabled={isSubmitting}
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isSubmitting ? 'animate-spin' : ''}`} />
                    <span>Recheck Content</span>
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={handleSaveReview}
                  >
                    <Save className="w-3.5 h-3.5 text-slate-600" />
                    <span>Save Review</span>
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => setStudioState('idle')}
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-slate-600" />
                    <span>New Scan</span>
                  </Button>

                  <Button
                    variant="primaryBlue"
                    size="sm"
                    className="gap-1.5 shadow-xs font-semibold"
                    onClick={handleSubmitForApproval}
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Submit for Approval</span>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6-Stage Animated Analysis Overlay (Only in simulated demo mode) */}
      <AnalysisProgressOverlay
        isOpen={apiClient.isMockMode() && studioState === 'analyzing'}
        onComplete={handleAnalysisComplete}
        workspaceName={currentWorkspace?.name}
      />

      {/* Guideline Inspector Drawer */}
      <GuidelineInspectorDrawer
        guideline={selectedGuideline}
        isOpen={isGuidelineDrawerOpen}
        onClose={() => setIsGuidelineDrawerOpen(false)}
      />

      {/* Version Comparison / Diff Modal */}
      <CompareDiffModal
        originalContent={originalContent}
        correctedContent={content}
        isOpen={isCompareModalOpen}
        onClose={() => setIsCompareModalOpen(false)}
        scoreBefore={realBackendScore !== null ? realBackendScore : (totalFindings === 0 ? 100 : 0)}
        scoreAfter={currentScore}
      />

      {/* Export Report Modal */}
      <ExportReportModal
        title={title}
        score={currentScore}
        findings={findings}
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
      />
    </motion.div>
  )
}
