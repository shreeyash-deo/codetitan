export interface Workspace {
  id: string
  name: string
  slug: string
  plan: 'Starter' | 'Growth' | 'Enterprise'
  brandCount: number
  complianceScore: number
  avatar?: string
  color: string
}

export interface WorkspaceContextValue {
  currentWorkspace: Workspace
  workspaces: Workspace[]
  switchWorkspace: (workspaceId: string) => void
}
