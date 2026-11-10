/**
 * BrandShield Team & Approvals Service
 * Handles multi-tier human reviewer routing, change requests, and approval sign-offs.
 *
 * Expected FastAPI Endpoints:
 * - GET  /api/v1/approvals/pending               (Fetch pending approval queue)
 * - POST /api/v1/approvals/{id}/approve          (Authorize publishing)
 * - POST /api/v1/approvals/{id}/request-changes  (Route back with revision notes)
 * - POST /api/v1/approvals/{id}/comments         (Append governance comment)
 */

import { apiClient } from './apiClient'
import type { ApprovalRequest, ReviewComment } from '@/types/api'
import { mockHistoricalReviews } from '@/data/mockHistoricalReviews'

export const approvalService = {
  /**
   * Fetch all assets pending approval sign-off
   * FastAPI Route: GET /api/v1/approvals/pending?brand_id={brand_id}
   */
  async getPendingApprovals(brandId?: string): Promise<ApprovalRequest[]> {
    if (apiClient.isMockMode()) {
      return mockHistoricalReviews
        .filter((r) => r.approvalStatus === 'pending' || r.approvalStatus === 'critical_issues')
        .map((r) => ({
          id: `appr-${r.id}`,
          reviewId: r.id,
          title: r.title,
          contentType: r.contentType,
          submittedBy: r.submittedBy,
          assignedReviewer: r.assignedReviewer,
          score: r.score,
          status: r.approvalStatus,
          reviewDate: r.reviewDate,
          contentExcerpt: r.originalContent.slice(0, 140) + '...',
          commentsCount: r.comments.length,
        }))
    }

    return apiClient.get<ApprovalRequest[]>('/api/v1/approvals/pending', {
      params: { brand_id: brandId },
    })
  },

  /**
   * Issue authoritative human approval and publishing clearance token
   * FastAPI Route: POST /api/v1/approvals/{review_id}/approve
   */
  async approveContent(reviewId: string, approvalComment?: string): Promise<{ success: boolean; certificateId: string }> {
    if (apiClient.isMockMode()) {
      return {
        success: true,
        certificateId: `CERT-BS-2026-${Math.floor(1000 + Math.random() * 9000)}`,
      }
    }

    return apiClient.post<{ success: boolean; certificateId: string }>(
      `/api/v1/approvals/${reviewId}/approve`,
      { comment: approvalComment }
    )
  },

  /**
   * Reject or request specific editorial/statutory revisions from author
   * FastAPI Route: POST /api/v1/approvals/{review_id}/request-changes
   */
  async requestChanges(reviewId: string, revisionNotes: string): Promise<{ success: boolean }> {
    if (apiClient.isMockMode()) {
      return { success: true }
    }

    return apiClient.post<{ success: boolean }>(
      `/api/v1/approvals/${reviewId}/request-changes`,
      { revisionNotes }
    )
  },

  /**
   * Append reviewer comment or guidance note to an asset record
   * FastAPI Route: POST /api/v1/approvals/{review_id}/comments
   */
  async addComment(reviewId: string, commentText: string): Promise<ReviewComment> {
    if (apiClient.isMockMode()) {
      return {
        id: `c-${Date.now()}`,
        authorName: 'Sarah Chen',
        authorRole: 'Brand Lead',
        text: commentText,
        timestamp: 'Just now',
      }
    }

    return apiClient.post<ReviewComment>(`/api/v1/approvals/${reviewId}/comments`, {
      text: commentText,
    })
  },
}
