import React, { useState } from 'react'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useAuth } from '@/context/AuthContext'
import { Building2, Plus, ArrowRight, Shield, ShieldCheck, Check, LogOut, Copy } from 'lucide-react'
import { CreateWorkspaceModal } from './CreateWorkspaceModal'
import { useToast } from '@/context/ToastContext'

export const WorkspaceSelectorView: React.FC = () => {
  const { workspaces, switchWorkspace } = useWorkspace()
  const { user, logout } = useAuth()
  const { success } = useToast()
  const [isModalOpen, setIsModalOpen] = useState(false)

  const copyOrgId = (e: React.MouseEvent, orgId?: string) => {
    e.stopPropagation()
    if (!orgId) return
    navigator.clipboard.writeText(orgId)
    success(`Organisation ID ${orgId} copied to clipboard.`, 'Copied')
  }

  return (
    <div className="min-h-screen w-screen bg-[#070C14] text-slate-100 flex items-center justify-center p-4 relative overflow-hidden select-none">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[350px] bg-blue-600/10 blur-[130px] rounded-full pointer-events-none" />

      <div className="w-full max-w-lg z-10 relative">
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white leading-tight">BrandShield</h1>
              <p className="text-xs text-slate-400">
                Signed in as <span className="text-slate-200 font-medium">{user?.name}</span> ({user?.email})
              </p>
            </div>
          </div>
          <button
            onClick={() => logout()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 border border-transparent hover:border-rose-900/40 transition-all cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>

        {workspaces.length === 0 ? (
          // Empty State: Create First Organisation
          <div className="bg-[#0D1524]/90 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mx-auto mb-4">
              <Building2 className="w-6 h-6" />
            </div>
            <h2 className="text-base font-semibold text-white mb-1.5">No Organisation Yet</h2>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mb-6 leading-relaxed">
              To begin governing brand guidelines, approving rules, and auditing marketing assets, create your first brand organisation.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="py-2.5 px-5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-xs font-semibold shadow-lg shadow-blue-600/20 inline-flex items-center gap-2 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Your Organisation</span>
            </button>
          </div>
        ) : (
          // Multiple Workspaces Selector
          <div className="bg-[#0D1524]/90 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-white">Select Active Organisation</h2>
                <p className="text-xs text-slate-400">Choose the organisation to access for this session</p>
              </div>
              <button
                onClick={() => setIsModalOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New Org</span>
              </button>
            </div>

            <div className="space-y-2.5">
              {workspaces.map((ws) => (
                <div
                  key={ws.id}
                  onClick={() => switchWorkspace(ws.id)}
                  className="p-3.5 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs text-white shrink-0"
                      style={{ backgroundColor: ws.color }}
                    >
                      {ws.name.substring(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white truncate group-hover:text-blue-300 transition-colors">
                          {ws.name}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-900/40 text-blue-300 border border-blue-800/40 font-medium">
                          {ws.role || 'Admin'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                          {ws.org_id || ws.orgId || `ORG-${ws.id}`}
                        </span>
                        <button
                          onClick={(e) => copyOrgId(e, ws.org_id || ws.orgId)}
                          title="Copy Organisation ID"
                          className="text-slate-500 hover:text-slate-300 p-0.5"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>

                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <CreateWorkspaceModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  )
}
