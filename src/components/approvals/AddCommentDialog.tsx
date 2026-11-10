import React, { useState } from 'react'
import type { HistoricalReviewRecord } from '@/types/approval'
import { Button } from '@/components/ui/button'
import { X, MessageSquare, Send } from 'lucide-react'

interface AddCommentDialogProps {
  review: HistoricalReviewRecord | null
  isOpen: boolean
  onClose: () => void
  onAddComment: (reviewId: string, commentText: string) => void
}

export const AddCommentDialog: React.FC<AddCommentDialogProps> = ({
  review,
  isOpen,
  onClose,
  onAddComment,
}) => {
  const [commentText, setCommentText] = useState('')

  if (!isOpen || !review) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!commentText.trim()) return
    onAddComment(review.id, commentText.trim())
    setCommentText('')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-md rounded-xl bg-white shadow-2xl border border-border p-6 space-y-4 animate-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <MessageSquare className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Add Reviewer Note
                </h3>
                <p className="text-xs text-slate-500">
                  Append a governance memo to this review record
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
            <span className="font-semibold text-slate-700">Asset: </span>
            <span className="text-slate-900 font-medium">{review.title}</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-800">
                Comment Text
              </label>
              <textarea
                required
                rows={3}
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Type reviewer feedback or clarification note..."
                className="w-full rounded-md border border-input bg-white p-3 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500 placeholder:text-slate-400"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button type="button" variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primaryBlue"
                size="sm"
                className="gap-1.5 font-semibold"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Post Comment</span>
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
