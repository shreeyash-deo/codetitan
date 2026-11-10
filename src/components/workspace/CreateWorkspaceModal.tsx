import React, { useState } from 'react'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useToast } from '@/context/ToastContext'
import { Building2, X, Plus, ShieldCheck, Loader2 } from 'lucide-react'

interface CreateWorkspaceModalProps {
  isOpen: boolean
  onClose: () => void
}

export const CreateWorkspaceModal: React.FC<CreateWorkspaceModalProps> = ({ isOpen, onClose }) => {
  const { createWorkspace } = useWorkspace()
  const { success, error: toastError } = useToast()
  const [orgName, setOrgName] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orgName.trim()) {
      setError('Please provide an organisation name.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      const created = await createWorkspace(orgName.trim())
      success(`Organisation "${created.name}" created with ID ${created.org_id || created.orgId}.`, 'Organisation Ready')
      setOrgName('')
      onClose()
    } catch (err: any) {
      const msg = err?.detail || err?.message || 'Failed to create organisation.'
      setError(msg)
      toastError(msg, 'Creation Error')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs select-none animate-in fade-in duration-150">
      <div className="w-full max-w-md bg-[#0D1524] border border-slate-800 rounded-2xl shadow-2xl p-6 text-slate-100 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          aria-label="Close modal"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Create Organisation</h2>
            <p className="text-xs text-slate-400">Provision a brand governance workspace</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Organisation / Brand Name
            </label>
            <input
              type="text"
              required
              autoFocus
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="e.g. NovaPay Global"
              className="w-full px-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-400 space-y-1.5">
            <div className="flex items-center gap-2 text-slate-300 font-medium">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Automatic Admin Authority</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              You will automatically become the primary <strong>Admin</strong> for this organisation and receive a secure, system-generated public Organisation ID (<code className="text-blue-300 font-mono">ORG-XXXXXXXX</code>).
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-3 py-2 text-xs font-medium rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !orgName.trim()}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white shadow-md shadow-blue-600/20 flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-all"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Provisioning...</span>
                </>
              ) : (
                <>
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Organisation</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
