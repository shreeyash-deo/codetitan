import React from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X, GitCompare, Copy, Check } from 'lucide-react'

interface CompareDiffModalProps {
  originalContent: string
  correctedContent: string
  isOpen: boolean
  onClose: () => void
  scoreBefore: number
  scoreAfter: number
}

export const CompareDiffModal: React.FC<CompareDiffModalProps> = ({
  originalContent,
  correctedContent,
  isOpen,
  onClose,
  scoreBefore,
  scoreAfter,
}) => {
  const [copied, setCopied] = React.useState(false)

  if (!isOpen) return null

  const handleCopy = () => {
    navigator.clipboard.writeText(correctedContent)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-4xl rounded-xl bg-white shadow-2xl border border-border p-6 space-y-5 animate-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <GitCompare className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Version Comparison: Original vs. Corrected
                </h3>
                <p className="text-xs text-slate-500">
                  Review how accepted suggestions remediate brand violations
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Badge variant="destructive" className="text-[10px]">
                  Original: {scoreBefore}/100
                </Badge>
                <span className="text-slate-400">→</span>
                <Badge variant="success" className="text-[10px]">
                  Remediated: {scoreAfter}/100
                </Badge>
              </div>

              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Side by Side Diff */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Original Draft */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-rose-700 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  Original Submitted Draft
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  {originalContent.length} chars
                </span>
              </div>
              <div className="p-4 rounded-lg bg-rose-50/40 border border-rose-200/80 text-xs font-serif text-slate-800 leading-relaxed min-h-[280px] whitespace-pre-wrap">
                {originalContent}
              </div>
            </div>

            {/* Remediated Draft */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Governance-Remediated Draft
                </span>
                <button
                  onClick={handleCopy}
                  className="text-[11px] text-blue-600 hover:underline flex items-center gap-1"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <div className="p-4 rounded-lg bg-emerald-50/40 border border-emerald-200/80 text-xs font-serif text-slate-800 leading-relaxed min-h-[280px] whitespace-pre-wrap">
                {correctedContent}
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-border">
            <span className="text-xs text-slate-500">
              Compliant copy remediates all identified brand and regulatory findings.
            </span>
            <Button variant="primaryBlue" size="sm" onClick={onClose}>
              Return to Studio
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
