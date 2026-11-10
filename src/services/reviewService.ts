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
import { studioPresets } from '@/data/mockStudioPresets'

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
}
