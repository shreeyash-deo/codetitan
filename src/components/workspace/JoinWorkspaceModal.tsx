import React, { useState } from 'react'
import { workspaceService } from '@/services/workspaceService'
import { useToast } from '@/context/ToastContext'
import { Building2, X, Users, ArrowRight, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'

interface JoinWorkspaceModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export const JoinWorkspaceModal: React.FC<JoinWorkspaceModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success, error: toastError } = useToast()
  const [orgId, setOrgId] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLookingUp, setIsLookingUp] = useState(false)
  const [previewOrg, setPreviewOrg] = useState<{ id: number; name: string; org_id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleOrgIdChange = async (val: string) => {
    const clean = val.toUpperCase().trim()
    setOrgId(clean)
    setError(null)
    setPreviewOrg(null)

    if (clean.length >= 7) {
      setIsLookingUp(true)
      try {
        const found = await workspaceService.lookupByOrgId(clean)
        setPreviewOrg(found)
      } catch {
        setPreviewOrg(null)
      } finally {
        setIsLookingUp(false)
      }
    }
  }

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orgId.trim()) {
      setError('Please enter a valid Organisation ID.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await workspaceService.joinOrganisation(orgId)
      success(
        `Join request submitted for ${previewOrg?.name || orgId}. Awaiting Admin approval.`,
        'Request Sent'
      )
      setOrgId('')
      setPreviewOrg(null)
      onSuccess()
      onClose()
    } catch (err: any) {
      const msg = err?.detail || err?.message || 'Failed to submit join request.'
      setError(msg)
      toastError(msg, 'Join Failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div className="w-full max-w-md bg-[#0D1524] border border-slate-800 rounded-2xl p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Join an Organisation</h3>
            <p className="text-xs text-slate-400">Request access to an existing BrandShield workspace</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        <form onSubmit={handleJoin} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-medium text-slate-300">
                Organisation ID
              </label>
              <span className="text-[11px] text-slate-400 font-mono">Format: ORG-XXXXXXXX</span>
            </div>
            <div className="relative">
              <Building2 className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                autoFocus
                value={orgId}
                onChange={(e) => handleOrgIdChange(e.target.value)}
                placeholder="e.g. ORG-792B6BA5"
                className="w-full pl-9 pr-3 py-2 text-xs font-mono uppercase tracking-wider rounded-lg bg-slate-900/80 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
              />
              {isLookingUp && (
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin absolute right-3 top-1/2 -translate-y-1/2" />
              )}
            </div>
          </div>

          {previewOrg && (
            <div className="p-3 rounded-lg bg-blue-950/40 border border-blue-800/50 flex items-center gap-2.5 text-xs text-blue-200 animate-in fade-in duration-150">
              <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
              <div>
                <span className="block font-semibold text-white">{previewOrg.name}</span>
                <span className="text-[11px] text-blue-300/80 font-mono">{previewOrg.org_id}</span>
              </div>
            </div>
          )}

          <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400">
            Requests are submitted for the <strong className="text-slate-200">Employee</strong> role. Access will activate once an organisation Admin approves your request.
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !orgId.trim()}
              className="py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 flex items-center gap-1.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <span>Submit Join Request</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
