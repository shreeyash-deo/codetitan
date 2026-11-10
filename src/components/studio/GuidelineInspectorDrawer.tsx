import React from 'react'
import type { SupportingGuideline } from '@/types/reviewStudio'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X, BookOpen, ShieldAlert, CheckCircle2, AlertOctagon, Scale } from 'lucide-react'

interface GuidelineInspectorDrawerProps {
  guideline: SupportingGuideline | null
  isOpen: boolean
  onClose: () => void
}

export const GuidelineInspectorDrawer: React.FC<GuidelineInspectorDrawerProps> = ({
  guideline,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !guideline) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div className="w-screen max-w-md bg-white shadow-2xl flex flex-col border-l border-border animate-in slide-in-from-right duration-200">
          {/* Header */}
          <div className="p-5 border-b border-border flex items-start justify-between bg-slate-50/70">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge variant="blue" className="text-[10px] font-mono">
                  {guideline.code}
                </Badge>
                <Badge
                  variant={guideline.enforcementLevel === 'Strict' ? 'default' : 'neutral'}
                  className="text-[10px]"
                >
                  {guideline.enforcementLevel} Enforcement
                </Badge>
              </div>
              <h2 className="text-base font-bold text-slate-900 mt-1">
                {guideline.title}
              </h2>
            </div>

            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Rule Definition & Boundaries
              </span>
              <p className="text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200">
                {guideline.description}
              </p>
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <Scale className="w-3.5 h-3.5 text-blue-600" />
                Statutory & Brand Rationale
              </span>
              <p className="text-slate-600 leading-relaxed p-3 rounded-lg bg-blue-50/50 border border-blue-100">
                {guideline.rationale}
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-slate-200 bg-white space-y-2">
              <div className="text-[11px] font-semibold text-slate-800">
                Audit Vector Parameters
              </div>
              <div className="text-[11px] text-slate-500 space-y-1">
                <div>• Embedding distance threshold: &gt; 0.84</div>
                <div>• Auto-flag on token occurrence: Enabled</div>
                <div>• Applicable Channels: All Omnichannel Collateral</div>
              </div>
            </div>
          </div>

          <div className="p-4 border-t border-border bg-slate-50 flex justify-end">
            <Button variant="outline" size="sm" onClick={onClose}>
              Dismiss
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
