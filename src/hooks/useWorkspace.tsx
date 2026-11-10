import React, { createContext, useContext, useState } from 'react'
import type { Workspace, WorkspaceContextValue } from '@/types/workspace'
import { mockWorkspaces } from '@/data/mockWorkspaces'

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined)

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace>(mockWorkspaces[0])

  const switchWorkspace = (workspaceId: string) => {
    const found = mockWorkspaces.find(w => w.id === workspaceId)
    if (found) {
      setCurrentWorkspace(found)
    }
  }

  return (
    <WorkspaceContext.Provider
      value={{
        currentWorkspace,
        workspaces: mockWorkspaces,
        switchWorkspace,
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
