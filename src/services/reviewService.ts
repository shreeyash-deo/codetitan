/**
 * BrandShield Content Review Service
 * Handles AI compliance inspection and suggestion generation.
 *
 * Expected FastAPI Endpoints:
 * - POST /api/v1/reviews/scan (Run AI model inference against brand guidelines)
 * - GET  /api/v1/reviews/{id} (Fetch historical scan report)
 */

import { apiClient } from './apiClient'
import type { ReviewRequest, ReviewResult, ComplianceFinding } from '@/types/api'
import type {
  ContentVersionSummary,
  ContentVersionDetail,
  VersionComparison,
} from '@/types/version'
import { studioPresets } from '@/data/mockStudioPresets'

export const normalizeVersionSummary = (raw: any): ContentVersionSummary => {
  if (!raw) return {} as ContentVersionSummary
  const versionNum = raw.versionNumber ?? raw.version_number ?? 1
  const hash = raw.contentHash ?? raw.content_hash ?? ''
  const score = raw.complianceScore ?? raw.compliance_score ?? 100
  const findingsCount = raw.findingsCount ?? raw.findings_count ?? (raw.findings ? raw.findings.length : 0)
  const auditStatus = raw.auditStatus ?? raw.audit_status ?? 'verified'
  const ruleSetVer = raw.ruleSetVersion ?? raw.rule_set_version ?? null
  const changeDesc = raw.changeDescription ?? raw.change_description ?? (versionNum === 1 ? 'Initial Submission' : 'Content updated')
  const authorId = raw.authorId ?? raw.author_id ?? null
  const authorName = raw.authorName ?? raw.author_name ?? null
  const versionState = raw.versionState ?? raw.version_state ?? (auditStatus === 'verified' ? 'audited' : 'saved_draft')
  const isCurrent = raw.isCurrent ?? raw.is_current ?? false
  const isOriginal = raw.isOriginal ?? raw.is_original ?? (versionNum === 1)
  const createdAt = raw.createdAt ?? raw.created_at ?? new Date().toISOString()

  return {
    ...raw,
    id: raw.id,
    reviewId: raw.reviewId ?? raw.review_id ?? 0,
    versionNumber: versionNum,
    contentHash: hash,
    complianceScore: score,
    status: raw.status || 'compliant',
    auditStatus: auditStatus,
    findingsCount: findingsCount,
    ruleSetVersion: ruleSetVer,
    summary: raw.summary ?? null,
    changeDescription: changeDesc,
    authorId: authorId,
    authorName: authorName,
    versionState: versionState,
    isCurrent: isCurrent,
    isOriginal: isOriginal,
    createdAt: createdAt,
    version_number: versionNum,
    content_hash: hash,
    compliance_score: score,
    findings_count: findingsCount,
    audit_status: auditStatus,
    rule_set_version: ruleSetVer,
    change_description: changeDesc,
    author_id: authorId,
    author_name: authorName,
    version_state: versionState,
    is_current: isCurrent,
    is_original: isOriginal,
    created_at: createdAt,
  }
}

export const normalizeVersionDetail = (raw: any): ContentVersionDetail => {
  const summary = normalizeVersionSummary(raw)
  const rawFindings = raw?.findings || []
  const findings: ComplianceFinding[] = rawFindings.map((f: any) => ({
    id: String(f.id),
    category: f.category || 'Unsupported claims',
    severity: f.severity === 'critical' ? 'critical' : (f.severity === 'major' || f.severity === 'moderate' ? 'moderate' : 'minor'),
    originalText: f.originalText || f.excerpt || f.snippet || '',
    explanation: f.explanation || '',
    supportingGuidelineCode: f.supportingGuidelineCode || f.guideline_reference || 'RULE',
    supportingGuidelineTitle: f.supportingGuidelineTitle || f.guideline_reference || '',
    suggestedCorrection: f.suggestedCorrection || f.suggested_correction || f.suggestion || '',
    confidence: f.confidence !== undefined ? (f.confidence <= 1.0 ? Math.round(f.confidence * 100) : Math.round(f.confidence)) : 95,
    resolved: f.resolved || f.status === 'accepted' || f.status === 'applied',
    status: f.status || 'open',
  }))

  return {
    ...summary,
    content: raw?.content || '',
    findings,
  }
}

export const reviewService = {
  /**
   * Submit marketing text or extracted document for AI compliance inspection
   * FastAPI Route: POST /api/v1/reviews/scan
   *
   * Request Payload: ReviewRequest
   * Response: ReviewResult
   */
  async submitContentForReview(payload: ReviewRequest, brandId?: string): Promise<ReviewResult> {
    if (apiClient.isMockMode()) {
      // Simulate realistic latency and deterministic mock result based on preset or text
      const matchingPreset = studioPresets.find(p => p.contentType === payload.contentType) || studioPresets[0]
      const findings: ComplianceFinding[] = matchingPreset.findings.map(f => ({
        id: f.id,
        category: f.category,
        severity: f.severity === 'info' ? 'minor' : (f.severity === 'warning' ? 'moderate' : 'critical'),
        originalText: f.originalText,
        explanation: f.explanation,
        supportingGuidelineCode: f.supportingGuideline.code,
        supportingGuidelineTitle: f.supportingGuideline.title,
        suggestedCorrection: f.suggestedCorrection,
        confidence: f.confidence,
        resolved: false,
      }))

      const hasCritical = findings.some(f => f.severity === 'critical')
      const calculatedScore = hasCritical ? 68 : 88

      return {
        id: `rev-${Date.now().toString().slice(-4)}`,
        title: payload.title,
        contentType: payload.contentType,
        channel: payload.channel,
        overallScore: calculatedScore,
        issuesCount: findings.length,
        status: hasCritical ? 'flagged' : 'approved',
        summary: hasCritical
          ? 'Identified statutory superlatives and terminology discrepancies with guidelines.'
          : 'High compliance alignment with active brand guidelines.',
        contentPreview: payload.content.slice(0, 160) + '...',
        findings,
        analyzedAt: new Date().toISOString(),
      }
    }

    return apiClient.post<ReviewResult>('/api/v1/reviews/scan', {
      ...payload,
      brandId,
    }, {
      params: { brand_id: brandId },
    })
  },

  /**
   * Fetch a previously scanned review report by ID
   * FastAPI Route: GET /api/v1/reviews/{id}
   */
  async getReviewById(reviewId: string): Promise<ReviewResult> {
    if (apiClient.isMockMode()) {
      const defaultPreset = studioPresets[0]
      return {
        id: reviewId,
        title: defaultPreset.title,
        contentType: defaultPreset.contentType,
        channel: 'Ad Creative',
        overallScore: 68,
        issuesCount: 3,
        status: 'flagged',
        summary: 'Contains statutory superlatives and deprecated terms.',
        contentPreview: defaultPreset.rawContent.slice(0, 150),
        findings: defaultPreset.findings.map(f => ({
          id: f.id,
          category: f.category,
          severity: f.severity === 'info' ? 'minor' : (f.severity === 'warning' ? 'moderate' : 'critical'),
          originalText: f.originalText,
          explanation: f.explanation,
          supportingGuidelineCode: f.supportingGuideline.code,
          supportingGuidelineTitle: f.supportingGuideline.title,
          suggestedCorrection: f.suggestedCorrection,
          confidence: f.confidence,
        })),
        analyzedAt: 'Today',
      }
    }

    return apiClient.get<ReviewResult>(`/api/v1/reviews/${reviewId}`)
  },

  /**
   * Fetch all historical versions for a review
   * FastAPI Route: GET /api/v1/reviews/{id}/versions
   */
  async getVersions(reviewId: string | number): Promise<ContentVersionSummary[]> {
    if (apiClient.isMockMode()) {
      return [
        normalizeVersionSummary({
          id: 1,
          reviewId: Number(reviewId) || 1,
          versionNumber: 1,
          contentHash: 'mock-hash-1',
          complianceScore: 75,
          status: 'in_review',
          auditStatus: 'verified',
          findingsCount: 3,
          changeDescription: 'Initial Submission',
          createdAt: new Date().toISOString(),
        }),
      ]
    }
    const res = await apiClient.get<any[]>(`/api/v1/reviews/${reviewId}/versions`)
    return (res || []).map(normalizeVersionSummary)
  },

  /**
   * Fetch specific content version with its immutable findings
   * FastAPI Route: GET /api/v1/reviews/{id}/versions/{versionNumber}
   */
  async getVersionDetail(
    reviewId: string | number,
    versionNumber: number
  ): Promise<ContentVersionDetail> {
    if (apiClient.isMockMode()) {
      return normalizeVersionDetail({
        id: versionNumber,
        reviewId: Number(reviewId) || 1,
        versionNumber,
        content: 'Mock content for version ' + versionNumber,
        contentHash: 'mock-hash-' + versionNumber,
        complianceScore: 80,
        status: 'in_review',
        auditStatus: 'verified',
        findingsCount: 1,
        changeDescription: 'Version snapshot',
        createdAt: new Date().toISOString(),
        findings: [],
      })
    }
    const res = await apiClient.get<any>(
      `/api/v1/reviews/${reviewId}/versions/${versionNumber}`
    )
    return normalizeVersionDetail(res)
  },

  /**
   * Compare two versions of a review
   * FastAPI Route: GET /api/v1/reviews/{id}/compare?source_version=X&target_version=Y
   */
  async compareVersions(
    reviewId: string | number,
    sourceVersion: number,
    targetVersion: number
  ): Promise<VersionComparison> {
    if (apiClient.isMockMode()) {
      return {
        reviewId: Number(reviewId) || 1,
        sourceVersion: normalizeVersionSummary({
          id: sourceVersion,
          reviewId: Number(reviewId) || 1,
          versionNumber: sourceVersion,
          contentHash: 'hash-src',
          complianceScore: 70,
          status: 'in_review',
          auditStatus: 'verified',
          findingsCount: 2,
          createdAt: new Date().toISOString(),
        }),
        targetVersion: normalizeVersionSummary({
          id: targetVersion,
          reviewId: Number(reviewId) || 1,
          versionNumber: targetVersion,
          contentHash: 'hash-tgt',
          complianceScore: 90,
          status: 'approved',
          auditStatus: 'verified',
          findingsCount: 0,
          createdAt: new Date().toISOString(),
        }),
        scoreBefore: 70,
        scoreAfter: 90,
        scoreDelta: 20,
        auditStatusBefore: 'verified',
        auditStatusAfter: 'verified',
        textDiff: [],
        rawDiff: '',
        findingsDelta: {
          resolved: [],
          new: [],
          persistent: [],
        },
      }
    }
    const res = await apiClient.get<any>(`/api/v1/reviews/${reviewId}/compare`, {
      params: {
        source_version: sourceVersion,
        target_version: targetVersion,
      },
    })
    return {
      ...res,
      sourceVersion: normalizeVersionSummary(res.source_version || res.sourceVersion),
      targetVersion: normalizeVersionSummary(res.target_version || res.targetVersion),
      scoreBefore: res.score_before ?? res.scoreBefore ?? 0,
      scoreAfter: res.score_after ?? res.scoreAfter ?? 0,
      scoreDelta: res.score_delta ?? res.scoreDelta ?? 0,
      auditStatusBefore: res.audit_status_before ?? res.auditStatusBefore ?? 'verified',
      auditStatusAfter: res.audit_status_after ?? res.auditStatusAfter ?? 'verified',
      textDiff: (res.text_diff || res.textDiff || []).map((h: any) => {
        const type = h.changeType || h.change_type || 'unchanged'
        return {
          ...h,
          changeType: type,
          change_type: type,
          content: h.content || '',
          oldStart: h.oldStart ?? h.old_start ?? null,
          oldLines: h.oldLines ?? h.old_lines ?? null,
          newStart: h.newStart ?? h.new_start ?? null,
          newLines: h.newLines ?? h.new_lines ?? null,
        }
      }),
      rawDiff: res.raw_diff ?? res.rawDiff ?? '',
      findingsDelta: {
        resolved: (res.findings_delta?.resolved || res.findingsDelta?.resolved || []).map((f: any) => ({
          ...f,
          originalText: f.originalText || f.excerpt || '',
          suggestedCorrection: f.suggestedCorrection || f.suggested_correction || '',
        })),
        new: (res.findings_delta?.new || res.findingsDelta?.new || []).map((f: any) => ({
          ...f,
          originalText: f.originalText || f.excerpt || '',
          suggestedCorrection: f.suggestedCorrection || f.suggested_correction || '',
        })),
        persistent: (res.findings_delta?.persistent || res.findingsDelta?.persistent || []).map((f: any) => ({
          ...f,
          originalText: f.originalText || f.excerpt || '',
          suggestedCorrection: f.suggestedCorrection || f.suggested_correction || '',
        })),
      },
      sourceContent: res.source_content ?? res.sourceContent ?? '',
      targetContent: res.target_content ?? res.targetContent ?? '',
      source_content: res.source_content ?? res.sourceContent ?? '',
      target_content: res.target_content ?? res.targetContent ?? '',
    }
  },
}
