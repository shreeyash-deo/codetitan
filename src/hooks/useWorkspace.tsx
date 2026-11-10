import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { Workspace, WorkspaceContextValue } from '@/types/workspace'
import { apiClient } from '@/services/apiClient'
import { useAuth } from '@/context/AuthContext'

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined)

const PALETTE = ['#0284c7', '#3b82f6', '#6366f1', '#8b5cf6', '#0ea5e9']

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isAuthenticated } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const refreshWorkspaces = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setWorkspaces([])
      setCurrentWorkspace(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const rawList = await apiClient.get<any[]>('/api/v1/workspaces')
      
      const mapped: Workspace[] = rawList.map((ws, idx) => {
        // Resolve current user's role in this workspace
        const membership = ws.members?.find((m: any) => String(m.user_id) === String(user.id))
        const userRole = membership?.role || 'Admin'

        return {
          id: String(ws.id),
          org_id: ws.org_id,
          orgId: ws.org_id,
          name: ws.name,
          slug: ws.name.toLowerCase().replace(/\s+/g, '-'),
          plan: 'Enterprise',
          brandCount: 1,
          complianceScore: 85,
          color: PALETTE[idx % PALETTE.length],
          role: userRole,
        }
      })

      setWorkspaces(mapped)

      const savedId = typeof window !== 'undefined' ? localStorage.getItem('brandshield_active_workspace_id') : null

      if (mapped.length === 0) {
        setCurrentWorkspace(null)
        if (typeof window !== 'undefined') {
          localStorage.removeItem('brandshield_active_workspace_id')
        }
      } else if (savedId && mapped.some((w) => w.id === savedId)) {
        const found = mapped.find((w) => w.id === savedId)!
        setCurrentWorkspace(found)
      } else if (mapped.length === 1) {
        setCurrentWorkspace(mapped[0])
        if (typeof window !== 'undefined') {
          localStorage.setItem('brandshield_active_workspace_id', mapped[0].id)
        }
      } else {
        // Multiple workspaces available with no saved preference:
        // Do not arbitrarily select one; require explicit user choice
        setCurrentWorkspace(null)
      }
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Failed to fetch workspaces from backend.')
      setWorkspaces([])
      setCurrentWorkspace(null)
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated, user])

  useEffect(() => {
    refreshWorkspaces()
  }, [refreshWorkspaces])

  const switchWorkspace = (workspaceId: string) => {
    const found = workspaces.find((w) => w.id === workspaceId)
    if (found) {
      setCurrentWorkspace(found)
      if (typeof window !== 'undefined') {
        localStorage.setItem('brandshield_active_workspace_id', found.id)
      }
    }
  }

  const createWorkspace = async (name: string): Promise<Workspace> => {
    const created = await apiClient.post<any>('/api/v1/workspaces', { name: name.trim() })
    const newWs: Workspace = {
      id: String(created.id),
      org_id: created.org_id,
      orgId: created.org_id,
      name: created.name,
      slug: created.name.toLowerCase().replace(/\s+/g, '-'),
      plan: 'Enterprise',
      brandCount: 1,
      complianceScore: 100,
      color: '#0284c7',
      role: 'Admin', // Creator automatically assigned Admin role
    }

    // Refresh list and select new workspace
    const updatedList = [...workspaces, newWs]
    setWorkspaces(updatedList)
    setCurrentWorkspace(newWs)
    if (typeof window !== 'undefined') {
      localStorage.setItem('brandshield_active_workspace_id', newWs.id)
    }

    return newWs
  }

  return (
    <WorkspaceContext.Provider
      value={{
        currentWorkspace,
        workspaces,
        switchWorkspace,
        createWorkspace,
        refreshWorkspaces,
        isLoading,
        error,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext)
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider')
  }
  return context
}
