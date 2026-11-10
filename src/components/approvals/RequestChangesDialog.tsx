import React, { useState } from 'react'
import type { HistoricalReviewRecord } from '@/types/approval'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X, AlertCircle, Send, MessageSquare } from 'lucide-react'

interface RequestChangesDialogProps {
  review: HistoricalReviewRecord | null
  isOpen: boolean
  onClose: () => void
  onSubmitChanges: (reviewId: string, revisionNotes: string) => void
}

export const RequestChangesDialog: React.FC<RequestChangesDialogProps> = ({
  review,
  isOpen,
  onClose,
  onSubmitChanges,
}) => {
  const [notes, setNotes] = useState('')

  if (!isOpen || !review) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!notes.trim()) return
    onSubmitChanges(review.id, notes.trim())
    setNotes('')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-lg rounded-xl bg-white shadow-2xl border border-border p-6 space-y-4 animate-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <AlertCircle className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Request Editorial Changes
                </h3>
                <p className="text-xs text-slate-500">
                  Route asset back to author with specific revision instructions
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <span className="font-semibold text-slate-700">Target Asset: </span>
            <span className="text-slate-900 font-medium">{review.title}</span>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Author: {review.submittedBy.name} ({review.submittedBy.email})
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-800">
                Required Revisions & Policy Guidance
              </label>
              <textarea
                required
                rows={4}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Explain the statutory violation or brand voice adjustment required before approval (e.g., 'Please reword paragraph 2 to acknowledge regulatory compliance in Singapore and Tokyo...')"
                className="w-full rounded-md border border-input bg-white p-3 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500 placeholder:text-slate-400"
              />
            </div>

            <p className="text-[11px] text-slate-500 italic">
              This comment will be logged in the immutable audit timeline and notify the author via email/Slack.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button type="button" variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="destructive"
                size="sm"
                className="gap-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Submit Change Request</span>
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
