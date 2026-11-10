import React, { useState } from 'react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useToast } from '@/context/ToastContext'
import { ChevronsUpDown, Check, Plus, ShieldCheck, Copy } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CreateWorkspaceModal } from '@/components/workspace/CreateWorkspaceModal'

interface WorkspaceSwitcherProps {
  collapsed?: boolean
}

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({ collapsed = false }) => {
  const { currentWorkspace, workspaces, switchWorkspace } = useWorkspace()
  const { success } = useToast()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  if (!currentWorkspace) {
    return null
  }

  const handleSelectWorkspace = (wsId: string, wsName: string) => {
    switchWorkspace(wsId)
    success(`Switched active organisation to ${wsName}.`, 'Organisation Changed')
  }

  const handleCopyOrgId = (e: React.MouseEvent, orgId?: string) => {
    e.stopPropagation()
    if (!orgId) return
    navigator.clipboard.writeText(orgId)
    success(`Copied Organisation ID: ${orgId}`, 'Copied')
  }

  const activeOrgId = currentWorkspace.org_id || currentWorkspace.orgId || `ORG-${currentWorkspace.id}`

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className={cn(
              'w-full flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-all duration-150',
              'bg-slate-900/60 hover:bg-slate-800/80 border border-white/5 hover:border-white/10 text-slate-200',
              'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500 cursor-pointer',
              collapsed ? 'justify-center px-1.5' : 'justify-between'
            )}
            title={collapsed ? `${currentWorkspace.name} (${activeOrgId})` : undefined}
          >
            <div className="flex items-center gap-2 min-w-0">
              <div
                className="flex items-center justify-center w-6 h-6 rounded-md text-[11px] font-bold text-white shrink-0 shadow-xs"
                style={{ backgroundColor: currentWorkspace.color }}
              >
                {currentWorkspace.name.substring(0, 2).toUpperCase()}
              </div>
              {!collapsed && (
                <div className="flex flex-col min-w-0 text-left">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-xs font-semibold text-slate-200 truncate">
                      {currentWorkspace.name}
                    </span>
                    <span className="text-[9px] px-1 py-0.2 rounded bg-blue-900/60 text-blue-300 font-medium">
                      {currentWorkspace.role || 'Unresolved'}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 truncate flex items-center gap-1 font-mono">
                    {activeOrgId}
                  </span>
                </div>
              )}
            </div>
            {!collapsed && (
              <ChevronsUpDown className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
            )}
          </button>
        </DropdownMenuTrigger>

        <DropdownMenuContent
          align={collapsed ? 'start' : 'start'}
          side={collapsed ? 'right' : 'bottom'}
          className="w-68 bg-slate-900 text-slate-200 border-slate-800 p-1.5 shadow-2xl"
        >
          <DropdownMenuLabel className="flex items-center justify-between px-2 py-1 text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
            <span>Organisations ({workspaces.length})</span>
            <button
              onClick={(e) => handleCopyOrgId(e, activeOrgId)}
              className="text-slate-400 hover:text-white flex items-center gap-1 normal-case tracking-normal text-[10px]"
              title="Copy current Organisation ID"
            >
              <Copy className="w-2.5 h-2.5" />
              <span>Copy ID</span>
            </button>
          </DropdownMenuLabel>

          <DropdownMenuSeparator className="bg-slate-800 my-1" />

          {workspaces.map((ws) => {
            const wsOrgId = ws.org_id || ws.orgId || `ORG-${ws.id}`
            const isSelected = ws.id === currentWorkspace.id

            return (
              <DropdownMenuItem
                key={ws.id}
                onClick={() => handleSelectWorkspace(ws.id, ws.name)}
                className={cn(
                  'flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-slate-800 focus:bg-slate-800 cursor-pointer',
                  isSelected && 'bg-slate-800/60'
                )}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className="flex items-center justify-center w-6 h-6 rounded text-[11px] font-bold text-white shrink-0"
                    style={{ backgroundColor: ws.color }}
                  >
                    {ws.name.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium text-slate-200 truncate">
                        {ws.name}
                      </span>
                      <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {ws.role || 'Unresolved'}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {wsOrgId}
                    </span>
                  </div>
                </div>
                {isSelected && (
                  <Check className="w-4 h-4 text-blue-400 shrink-0 ml-2" />
                )}
              </DropdownMenuItem>
            )
          })}

          <DropdownMenuSeparator className="bg-slate-800 my-1" />

          <DropdownMenuItem
            className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-blue-300 hover:text-blue-200 hover:bg-blue-950/40 rounded cursor-pointer"
            onClick={() => setIsCreateModalOpen(true)}
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create New Organisation</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CreateWorkspaceModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />
    </>
  )
}
