import { apiClient } from './apiClient'

export interface JoinRequest {
  id: number
  workspace_id: number
  user_id: number
  role: string
  status: string
  name: string
  email: string
  created_at?: string
  user_name?: string
  user_email?: string
}

export interface UserPendingRequest {
  workspace_id: number
  org_id: string
  org_name: string
  role: string
  status: string
}

export interface WorkspaceMemberInfo {
  id: number
  workspace_id: number
  user_id: number
  role: string
  status: string
  user?: {
    id: number
    name: string
    email: string
    role?: string
  }
  user_name?: string
  user_email?: string
}

export const workspaceService = {
  /**
   * Request to join an existing organization by ORG ID
   */
  async joinOrganisation(org_id: string): Promise<any> {
    return apiClient.post('/api/v1/workspaces/join', {
      org_id: org_id.trim().toUpperCase(),
    })
  },

  /**
   * List the current user's pending join requests
   */
  async getUserPendingRequests(): Promise<UserPendingRequest[]> {
    return apiClient.get<UserPendingRequest[]>('/api/v1/workspaces/pending-requests')
  },

  /**
   * Cancel the current user's pending join request for a workspace
   */
  async cancelJoinRequest(workspaceId: number | string): Promise<any> {
    return apiClient.delete(`/api/v1/workspaces/pending-requests/${workspaceId}`)
  },

  /**
   * Look up workspace details by ORG ID (e.g. to preview before joining)
   */
  async lookupByOrgId(org_id: string): Promise<{ id: number; name: string; org_id: string }> {
    return apiClient.get(`/api/v1/workspaces/lookup?org_id=${encodeURIComponent(org_id.trim().toUpperCase())}`)
  },

  /**
   * List all pending join requests for an organization (Admin only)
   */
  async getWorkspaceJoinRequests(workspaceId: number | string): Promise<JoinRequest[]> {
    return apiClient.get<JoinRequest[]>(`/api/v1/workspaces/${workspaceId}/join-requests`)
  },

  /**
   * Approve a pending join request (Admin only)
   */
  async approveJoinRequest(workspaceId: number | string, userId: number | string): Promise<any> {
    return apiClient.post(`/api/v1/workspaces/${workspaceId}/join-requests/${userId}/approve`)
  },

  /**
   * Reject a pending join request (Admin only)
   */
  async rejectJoinRequest(workspaceId: number | string, userId: number | string): Promise<any> {
    return apiClient.post(`/api/v1/workspaces/${workspaceId}/join-requests/${userId}/reject`)
  },

  /**
   * Update a member's role between Employee and Reviewer (Admin only)
   */
  async updateMemberRole(
    workspaceId: number | string,
    userId: number | string,
    role: 'Employee' | 'Reviewer'
  ): Promise<any> {
    return apiClient.patch(`/api/v1/workspaces/${workspaceId}/members/${userId}/role`, { role })
  },

  /**
   * List all approved members for an organization
   */
  async getMembers(workspaceId: number | string): Promise<WorkspaceMemberInfo[]> {
    return apiClient.get<WorkspaceMemberInfo[]>(`/api/v1/workspaces/${workspaceId}/members`)
  },
}
