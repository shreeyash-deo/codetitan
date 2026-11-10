/**
 * BrandShield Brand & Workspace Service
 * Manages brand workspaces, multi-tenant organizations, and telemetry.
 *
 * Expected FastAPI Endpoints:
 * - GET    /api/v1/brands             (List all brands in current org)
 * - GET    /api/v1/brands/{brand_id}   (Get brand details)
 * - PATCH  /api/v1/brands/{brand_id}   (Update brand parameters/strictness)
 * - GET    /api/v1/brands/{brand_id}/telemetry (Aggregated compliance statistics)
 */

import { apiClient } from './apiClient'
import type { Brand } from '@/types/api'
import type { Workspace } from '@/types/workspace'
import { mockWorkspaces } from '@/data/mockWorkspaces'

export interface BrandTelemetry {
  overallScore: number
  activeRulesCount: number
  contentReviewedCount: number
  pendingApprovalsCount: number
  criticalIssuesCount: number
  lastUpdated: string
}

export const brandService = {
  /**
   * Fetch all organizations / workspaces available to user
   * FastAPI Route: GET /api/v1/brands
   */
  async getBrands(): Promise<Brand[]> {
    if (apiClient.isMockMode()) {
      return mockWorkspaces.map((ws) => ({
        id: ws.id,
        name: ws.name,
        slug: ws.slug,
        plan: ws.plan,
        complianceScore: ws.complianceScore,
        activeRulesCount: 48,
        brandColor: ws.color,
      }))
    }

    return apiClient.get<Brand[]>('/api/v1/brands')
  },

  /**
   * Get brand details by ID
   * FastAPI Route: GET /api/v1/brands/{brand_id}
   */
  async getBrandById(brandId: string): Promise<Brand> {
    if (apiClient.isMockMode()) {
      const found = mockWorkspaces.find((w) => w.id === brandId) || mockWorkspaces[0]
      return {
        id: found.id,
        name: found.name,
        slug: found.slug,
        plan: found.plan,
        complianceScore: found.complianceScore,
        activeRulesCount: 48,
        brandColor: found.color,
      }
    }

    return apiClient.get<Brand>(`/api/v1/brands/${brandId}`)
  },

  /**
   * Fetch live telemetry and KPI health metrics for dashboard
   * FastAPI Route: GET /api/v1/brands/{brand_id}/telemetry
   */
  async getBrandTelemetry(brandId: string): Promise<BrandTelemetry> {
    if (apiClient.isMockMode()) {
      return {
        overallScore: 87,
        activeRulesCount: 48,
        contentReviewedCount: 124,
        pendingApprovalsCount: 8,
        criticalIssuesCount: 3,
        lastUpdated: 'Today at 2:15 PM',
      }
    }

    return apiClient.get<BrandTelemetry>(`/api/v1/brands/${brandId}/telemetry`)
  },

  /**
   * Update brand parameters (e.g., sensitivity threshold, integrations)
   * FastAPI Route: PATCH /api/v1/brands/{brand_id}
   */
  async updateBrand(brandId: string, payload: Partial<Brand>): Promise<Brand> {
    if (apiClient.isMockMode()) {
      const current = await this.getBrandById(brandId)
      return { ...current, ...payload }
    }

    return apiClient.patch<Brand>(`/api/v1/brands/${brandId}`, payload)
  },
}
