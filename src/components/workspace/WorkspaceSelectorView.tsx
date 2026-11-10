import React, { useState, useEffect, useCallback } from 'react'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useAuth } from '@/context/AuthContext'
import { Building2, Plus, ArrowRight, Shield, LogOut, Copy, Clock, Users, XCircle, AlertCircle, RefreshCw } from 'lucide-react'
import { CreateWorkspaceModal } from './CreateWorkspaceModal'
import { JoinWorkspaceModal } from './JoinWorkspaceModal'
import { workspaceService, type UserPendingRequest } from '@/services/workspaceService'
import { useToast } from '@/context/ToastContext'

export const WorkspaceSelectorView: React.FC = () => {
  const { workspaces, switchWorkspace, refreshWorkspaces } = useWorkspace()
  const { user, logout } = useAuth()
  const { success, error: toastError } = useToast()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false)
  const [pendingRequests, setPendingRequests] = useState<UserPendingRequest[]>([])
  const [isLoadingPending, setIsLoadingPending] = useState(true)
  const [isCancelling, setIsCancelling] = useState<number | null>(null)

  const fetchPending = useCallback(async () => {
    setIsLoadingPending(true)
    try {
      const data = await workspaceService.getUserPendingRequests()
      setPendingRequests(data || [])
    } catch {
      setPendingRequests([])
    } finally {
      setIsLoadingPending(false)
    }
  }, [])

  useEffect(() => {
    fetchPending()
  }, [fetchPending])

  const copyOrgId = (e: React.MouseEvent, orgId?: string) => {
    e.stopPropagation()
    if (!orgId) return
    navigator.clipboard.writeText(orgId)
    success(`Organisation ID ${orgId} copied to clipboard.`, 'Copied')
  }

  const handleCancelRequest = async (workspaceId: number, orgName: string) => {
    setIsCancelling(workspaceId)
    try {
      await workspaceService.cancelJoinRequest(workspaceId)
      success(`Join request for ${orgName} cancelled.`, 'Cancelled')
      await fetchPending()
      await refreshWorkspaces()
    } catch (err: any) {
      toastError(err?.detail || err?.message || 'Failed to cancel request.', 'Error')
    } finally {
      setIsCancelling(null)
    }
  }

  const handleModalSuccess = async () => {
    await fetchPending()
    await refreshWorkspaces()
  }

  const hasNoApprovedWorkspaces = workspaces.length === 0
  const hasPendingRequests = pendingRequests.length > 0

  return (
    <div className="min-h-screen w-screen bg-[#070C14] text-slate-100 flex items-center justify-center p-4 relative overflow-hidden select-none">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[350px] bg-blue-600/10 blur-[130px] rounded-full pointer-events-none" />

      <div className="w-full max-w-lg z-10 relative">
        {/* Top Header */}
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

        {/* 1. DEDICATED PENDING APPROVAL VIEW (User has no approved org, only pending requests) */}
        {hasNoApprovedWorkspaces && hasPendingRequests ? (
          <div className="bg-[#0D1524]/90 backdrop-blur-xl border border-amber-900/40 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
                  <Clock className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-white">Membership Request Pending</h2>
                  <p className="text-xs text-slate-400">Awaiting Organisation Administrator sign-off</p>
                </div>
              </div>
              <button
                onClick={() => {
                  fetchPending()
                  refreshWorkspaces()
                }}
                title="Refresh Status"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              {pendingRequests.map((req) => (
                <div
                  key={req.workspace_id}
                  className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-white">{req.org_name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs font-mono text-slate-400">{req.org_id}</span>
                        <button
                          onClick={(e) => copyOrgId(e, req.org_id)}
                          className="text-slate-500 hover:text-slate-300 p-0.5"
                          title="Copy Org ID"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5">
                      <Clock className="w-3 h-3" />
                      <span>Pending Approval</span>
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                    <span className="text-slate-400">
                      Requested Role: <strong className="text-slate-200">Employee</strong>
                    </span>
                    <button
                      onClick={() => handleCancelRequest(req.workspace_id, req.org_name)}
                      disabled={isCancelling === req.workspace_id}
                      className="text-rose-400 hover:text-rose-300 flex items-center gap-1 text-[11px] hover:underline cursor-pointer disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>{isCancelling === req.workspace_id ? 'Cancelling...' : 'Cancel Request'}</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 leading-relaxed space-y-1">
              <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                <span>Access Restriction Notice</span>
              </div>
              <p>
                An organisation administrator must approve your request before you can access workspace guidelines, review workflows, and compliance dashboards.
              </p>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 gap-3">
              <button
                onClick={() => setIsJoinModalOpen(true)}
                className="flex-1 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition-all cursor-pointer text-center"
              >
                Join Different Organisation
              </button>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="flex-1 py-2 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 transition-all cursor-pointer text-center"
              >
                Create New Organisation
              </button>
            </div>
          </div>
        ) : hasNoApprovedWorkspaces && !hasPendingRequests ? (
          // 2. EMPTY STATE: NO ORGS AND NO PENDING REQUESTS
          <div className="bg-[#0D1524]/90 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mx-auto mb-4">
              <Building2 className="w-6 h-6" />
            </div>
            <h2 className="text-base font-semibold text-white mb-1.5">No Organisation Yet</h2>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mb-6 leading-relaxed">
              To begin governing brand guidelines, approving rules, and auditing marketing assets, create an organisation or join an existing team.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="w-full sm:w-auto py-2.5 px-5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-xs font-semibold shadow-lg shadow-blue-600/20 inline-flex items-center justify-center gap-2 transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Create Organisation (Admin)</span>
              </button>
              <button
                onClick={() => setIsJoinModalOpen(true)}
                className="w-full sm:w-auto py-2.5 px-5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold inline-flex items-center justify-center gap-2 transition-all cursor-pointer"
              >
                <Users className="w-4 h-4" />
                <span>Join via ORG ID</span>
              </button>
            </div>
          </div>
        ) : (
          // 3. SELECTOR VIEW: USER HAS ONE OR MORE APPROVED ORGANISATIONS
          <div className="bg-[#0D1524]/90 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Select Active Organisation</h2>
                <p className="text-xs text-slate-400">Choose the organisation to access for this session</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsJoinModalOpen(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors cursor-pointer"
                >
                  <Users className="w-3.5 h-3.5" />
                  <span>Join Org</span>
                </button>
                <button
                  onClick={() => setIsCreateModalOpen(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>New Org</span>
                </button>
              </div>
            </div>

            {/* If user also has pending requests */}
            {hasPendingRequests && (
              <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-900/40 text-xs text-amber-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>You have {pendingRequests.length} pending organisation join request(s).</span>
                </div>
                <span className="text-[11px] font-mono text-amber-400/80">Pending approval</span>
              </div>
            )}

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
                          {ws.role || 'Unresolved'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                          {ws.org_id || ws.orgId || `ORG-${ws.id}`}
                        </span>
                        <button
                          onClick={(e) => copyOrgId(e, ws.org_id || ws.orgId)}
                          title="Copy Organisation ID"
                          className="text-slate-500 hover:text-slate-300 p-0.5 cursor-pointer"
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

      <CreateWorkspaceModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      <JoinWorkspaceModal
        isOpen={isJoinModalOpen}
        onClose={() => setIsJoinModalOpen(false)}
        onSuccess={handleModalSuccess}
      />
    </div>
  )
}
