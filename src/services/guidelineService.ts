/**
 * BrandShield Guideline & Knowledge Base Service
 * Handles approved guidelines, AI candidate extraction queue, and source documents.
 *
 * Expected FastAPI Endpoints:
 * - GET    /api/v1/guidelines/rules               (Get approved rules)
 * - POST   /api/v1/guidelines/rules               (Create approved rule)
 * - PUT    /api/v1/guidelines/rules/{rule_id}     (Update approved rule)
 * - DELETE /api/v1/guidelines/rules/{rule_id}     (Delete approved rule)
 * - GET    /api/v1/guidelines/candidates          (Get pending AI extractions)
 * - POST   /api/v1/guidelines/candidates/{id}/approve (Promote candidate)
 * - POST   /api/v1/guidelines/candidates/{id}/reject  (Dismiss candidate)
 * - GET    /api/v1/guidelines/documents           (List source documents)
 * - POST   /api/v1/guidelines/documents/upload    (Upload & trigger AI parsing)
 */

import { apiClient } from './apiClient'
import type {
  BrandGuideline,
  ExtractedRule,
  SourceDocument,
  GuidelineCategoryType,
} from '@/types/api'
import {
  initialApprovedRules,
  initialPendingCandidates,
  initialSourceDocuments,
} from '@/data/mockKnowledgeBase'

export const guidelineService = {
  // ==========================================================================
  // Approved Rules
  // ==========================================================================

  /**
   * Fetch all approved rules for a brand
   * FastAPI Route: GET /api/v1/guidelines/rules?brand_id={brand_id}
   */
  async getApprovedRules(brandId?: string): Promise<BrandGuideline[]> {
    if (apiClient.isMockMode()) {
      return initialApprovedRules.map((r) => ({
        id: r.id,
        code: r.code,
        category: r.category as GuidelineCategoryType,
        subCategory: r.subCategory,
        title: r.title,
        description: r.description,
        enforcementLevel: r.enforcementLevel,
        approvedExample: r.examples?.approved,
        prohibitedExample: r.examples?.prohibited,
        sourceDocument: r.sourceDocument,
        sourcePage: r.sourcePage,
        lastUpdated: r.lastUpdated,
        updatedBy: r.updatedBy,
      }))
    }

    return apiClient.get<BrandGuideline[]>('/api/v1/guidelines/rules', {
      params: { brand_id: brandId },
    })
  },

  /**
   * Create a new approved guideline rule
   * FastAPI Route: POST /api/v1/guidelines/rules
   */
  async createApprovedRule(payload: Omit<BrandGuideline, 'id'>, brandId?: string): Promise<BrandGuideline> {
    if (apiClient.isMockMode()) {
      return {
        ...payload,
        id: `rule-${Date.now()}`,
      }
    }

    return apiClient.post<BrandGuideline>('/api/v1/guidelines/rules', payload, {
      params: { brand_id: brandId },
    })
  },

  /**
   * Update an existing guideline rule
   * FastAPI Route: PUT /api/v1/guidelines/rules/{rule_id}
   */
  async updateApprovedRule(ruleId: string, payload: Partial<BrandGuideline>): Promise<BrandGuideline> {
    if (apiClient.isMockMode()) {
      return {
        id: ruleId,
        code: payload.code || 'BV-01',
        category: payload.category || 'Brand Voice',
        subCategory: payload.subCategory || 'General',
        title: payload.title || 'Updated Rule',
        description: payload.description || '',
        enforcementLevel: payload.enforcementLevel || 'Strict',
        lastUpdated: 'Just now',
        updatedBy: 'Sarah Chen',
        ...payload,
      } as BrandGuideline
    }

    return apiClient.put<BrandGuideline>(`/api/v1/guidelines/rules/${ruleId}`, payload)
  },

  /**
   * Delete an approved rule
   * FastAPI Route: DELETE /api/v1/guidelines/rules/{rule_id}
   */
  async deleteApprovedRule(ruleId: string): Promise<void> {
    if (apiClient.isMockMode()) return
    return apiClient.delete(`/api/v1/guidelines/rules/${ruleId}`)
  },

  // ==========================================================================
  // Candidate Extraction Review Queue
  // ==========================================================================

  /**
   * Fetch pending candidate rules extracted by AI
   * FastAPI Route: GET /api/v1/guidelines/candidates?brand_id={brand_id}
   */
  async getPendingCandidates(brandId?: string): Promise<ExtractedRule[]> {
    if (apiClient.isMockMode()) {
      return initialPendingCandidates.map((c) => ({
        id: c.id,
        category: c.category as GuidelineCategoryType,
        subCategory: c.subCategory,
        title: c.title,
        extractedText: c.extractedText,
        rationale: c.rationale,
        sourceDocument: c.sourceDocument,
        sourceSection: c.sourceSection,
        confidence: c.confidence,
        dateExtracted: c.dateExtracted,
        suggestedEnforcement: c.suggestedEnforcement,
        status: 'pending',
      }))
    }

    return apiClient.get<ExtractedRule[]>('/api/v1/guidelines/candidates', {
      params: { brand_id: brandId },
    })
  },

  /**
   * Authorize and promote a candidate rule into official guidelines
   * FastAPI Route: POST /api/v1/guidelines/candidates/{id}/approve
   */
  async approveCandidate(candidateId: string): Promise<BrandGuideline> {
    if (apiClient.isMockMode()) {
      const candidate = initialPendingCandidates.find((c) => c.id === candidateId)
      return {
        id: `rule-promoted-${Date.now()}`,
        code: 'CR-99',
        category: candidate?.category as GuidelineCategoryType || 'Claims & Restrictions',
        subCategory: candidate?.subCategory || 'Promoted Rule',
        title: candidate?.title || 'Approved Rule',
        description: candidate?.extractedText || '',
        enforcementLevel: candidate?.suggestedEnforcement || 'Strict',
        sourceDocument: candidate?.sourceDocument,
        sourcePage: candidate?.sourceSection,
        lastUpdated: 'Just now',
        updatedBy: 'Sarah Chen (Brand Lead)',
      }
    }

    return apiClient.post<BrandGuideline>(`/api/v1/guidelines/candidates/${candidateId}/approve`)
  },

  /**
   * Reject a candidate rule from the review queue
   * FastAPI Route: POST /api/v1/guidelines/candidates/{id}/reject
   */
  async rejectCandidate(candidateId: string): Promise<void> {
    if (apiClient.isMockMode()) return
    return apiClient.post(`/api/v1/guidelines/candidates/${candidateId}/reject`)
  },

  // ==========================================================================
  // Source Documents
  // ==========================================================================

  /**
   * Get list of uploaded brand documents
   * FastAPI Route: GET /api/v1/guidelines/documents
   */
  async getSourceDocuments(brandId?: string): Promise<SourceDocument[]> {
    if (apiClient.isMockMode()) {
      return initialSourceDocuments
    }

    return apiClient.get<SourceDocument[]>('/api/v1/guidelines/documents', {
      params: { brand_id: brandId },
    })
  },

  /**
   * Upload PDF/DOCX and trigger asynchronous AI knowledge extraction
   * FastAPI Route: POST /api/v1/guidelines/documents/upload (multipart/form-data)
   */
  async uploadSourceDocument(file: File, brandId?: string): Promise<SourceDocument> {
    if (apiClient.isMockMode()) {
      return {
        id: `doc-${Date.now()}`,
        name: file.name,
        format: file.name.toLowerCase().endsWith('.docx') ? 'DOCX' : 'PDF',
        size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        pages: 18,
        uploadedAt: 'Today',
        uploadedBy: 'Verified User',
        status: 'extracted',
        extractedCandidatesCount: 2,
        approvedRulesCount: 0,
      }
    }

    const formData = new FormData()
    formData.append('file', file)
    if (brandId) {
      formData.append('brand_id', brandId)
    }

    return apiClient.upload<SourceDocument>('/api/v1/guidelines/documents/upload', formData, {
      params: { brand_id: brandId },
    })
  },
}
