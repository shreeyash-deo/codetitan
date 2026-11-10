export interface Workspace {
  id: string
  org_id?: string
  orgId?: string
  name: string
  slug: string
  plan: 'Starter' | 'Growth' | 'Enterprise'
  brandCount: number
  complianceScore: number
  avatar?: string
  color: string
  role?: string
}

export interface WorkspaceContextValue {
  currentWorkspace: Workspace | null
  workspaces: Workspace[]
  switchWorkspace: (workspaceId: string) => void
  createWorkspace: (name: string) => Promise<Workspace>
  refreshWorkspaces: () => Promise<void>
  isLoading: boolean
  error: string | null
}
