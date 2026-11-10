import React from 'react'
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
import { ChevronsUpDown, Check, Plus, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

interface WorkspaceSwitcherProps {
  collapsed?: boolean
}

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({ collapsed = false }) => {
  const { currentWorkspace, workspaces, switchWorkspace } = useWorkspace()
  const { info, success } = useToast()

  const handleSelectWorkspace = (wsId: string, wsName: string) => {
    switchWorkspace(wsId)
    success(`Switched active workspace context to ${wsName}.`, 'Workspace Changed')
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            'w-full flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-all duration-150',
            'bg-slate-900/60 hover:bg-slate-800/80 border border-white/5 hover:border-white/10 text-slate-200',
            'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500',
            collapsed ? 'justify-center px-1.5' : 'justify-between'
          )}
          title={collapsed ? currentWorkspace.name : undefined}
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
                <span className="text-xs font-medium text-slate-200 truncate">
                  {currentWorkspace.name}
                </span>
                <span className="text-[10px] text-slate-400 truncate flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-blue-400 inline" />
                  {currentWorkspace.complianceScore}% compliance
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
        className="w-64 bg-slate-900 text-slate-200 border-slate-800 p-1.5 shadow-2xl"
      >
        <DropdownMenuLabel className="text-[10px] uppercase tracking-wider text-slate-400 px-2 py-1">
          Workspaces ({workspaces.length})
        </DropdownMenuLabel>
        
        {workspaces.map((ws) => (
          <DropdownMenuItem
            key={ws.id}
            onClick={() => handleSelectWorkspace(ws.id, ws.name)}
            className="flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-slate-800 focus:bg-slate-800 cursor-pointer"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className="flex items-center justify-center w-6 h-6 rounded text-[11px] font-bold text-white shrink-0"
                style={{ backgroundColor: ws.color }}
              >
                {ws.name.substring(0, 2).toUpperCase()}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-medium text-slate-200 truncate">
                  {ws.name}
                </span>
                <span className="text-[10px] text-slate-400">
                  {ws.plan} • {ws.brandCount} brand profiles
                </span>
              </div>
            </div>
            {ws.id === currentWorkspace.id && (
              <Check className="w-4 h-4 text-blue-400 shrink-0 ml-2" />
            )}
          </DropdownMenuItem>
        ))}

        <DropdownMenuSeparator className="bg-slate-800 my-1" />

        <DropdownMenuItem
          className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-slate-800 rounded cursor-pointer"
          onClick={() => info('Organization multi-tenant workspace provisioning is active in Enterprise plan.', 'Workspace Tier')}
        >
          <Plus className="w-3.5 h-3.5 text-slate-400" />
          <span>Provision New Workspace</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
