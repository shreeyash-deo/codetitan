/**
 * BrandShield Review History & Audit Ledger Service
 * Fetches immutable compliance records, version diffs, and verification certificates.
 *
 * Expected FastAPI Endpoints:
 * - GET /api/v1/history          (List historical audits with filters & pagination)
 * - GET /api/v1/history/{id}     (Get full historical audit record & diff)
 * - GET /api/v1/history/export   (Download CSV or PDF compliance certificate)
 */

import { apiClient } from './apiClient'
import type { ReviewHistory } from '@/types/api'
import { mockHistoricalReviews } from '@/data/mockHistoricalReviews'

export interface HistoryFilterParams {
  status?: string
  search?: string
  channel?: string
  brandId?: string
  limit?: number
  offset?: number
}

export const historyService = {
  /**
   * Fetch historical review ledger records
   * FastAPI Route: GET /api/v1/history
   */
  async getReviewHistory(params?: HistoryFilterParams): Promise<ReviewHistory[]> {
    if (apiClient.isMockMode()) {
      return mockHistoricalReviews.map((r) => ({
        id: r.id,
        title: r.title,
        contentType: r.contentType,
        channel: r.channel,
        submittedBy: r.submittedBy,
        assignedReviewer: r.assignedReviewer,
        score: r.score,
        violationsCount: r.violationsCount,
        reviewDate: r.reviewDate,
        approvalStatus: r.approvalStatus,
        originalContent: r.originalContent,
        correctedContent: r.correctedContent,
        findings: r.findings.map(f => ({
          id: f.id,
          category: f.category,
          severity: f.severity,
          originalText: f.snippet,
          explanation: f.explanation,
          supportingGuidelineCode: 'RULE-LEG-1.1',
          supportingGuidelineTitle: 'Prohibited Superlatives',
          suggestedCorrection: f.suggestion,
          confidence: 96,
        })),
        acceptedSuggestionsCount: r.acceptedSuggestionsCount,
        rejectedSuggestionsCount: r.rejectedSuggestionsCount,
        comments: r.comments,
        timeline: r.timeline,
      }))
    }

    const queryParams: Record<string, any> = { ...(params || {}) }
    if (queryParams.brandId && !queryParams.brand_id) {
      queryParams.brand_id = queryParams.brandId
      delete queryParams.brandId
    }

    return apiClient.get<ReviewHistory[]>('/api/v1/history', {
      params: queryParams,
    })
  },

  /**
   * Fetch single historical review by ID
   * FastAPI Route: GET /api/v1/history/{id}
   */
  async getHistoryById(id: string): Promise<ReviewHistory> {
    if (apiClient.isMockMode()) {
      const records = await this.getReviewHistory()
      const found = records.find((r) => r.id === id)
      if (!found) {
        throw new Error(`Review record ${id} not found`)
      }
      return found
    }

    return apiClient.get<ReviewHistory>(`/api/v1/history/${id}`)
  },

  /**
   * Export audit ledger to CSV
   * FastAPI Route: GET /api/v1/history/export?format=csv
   */
  async exportAuditCsv(brandId?: string): Promise<Blob> {
    if (apiClient.isMockMode()) {
      const csvContent = 'ID,Title,ContentType,Author,Reviewer,Score,Status,Date\n' +
        mockHistoricalReviews.map(r =>
          `"${r.id}","${r.title}","${r.contentType}","${r.submittedBy.name}","${r.assignedReviewer.name}",${r.score},"${r.approvalStatus}","${r.reviewDate}"`
        ).join('\n')
      return new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    }

    const token = localStorage.getItem('brandshield_auth_token')
    const response = await fetch(`${apiClient['baseUrl']}/api/v1/history/export?format=csv&brand_id=${brandId || ''}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    return response.blob()
  },
}
