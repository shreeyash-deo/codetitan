import React, { useState } from 'react'
import type { StudioFinding } from '@/types/reviewStudio'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Check,
  X,
  Edit3,
  BookOpen,
  Sparkles,
  AlertTriangle,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle,
  CornerDownRight,
} from 'lucide-react'

interface FindingCardProps {
  finding: StudioFinding
  onAccept: (findingId: string) => void
  onReject: (findingId: string) => void
  onManualEdit: (findingId: string, customReplacement: string) => void
  onViewGuideline: (finding: StudioFinding) => void
  isSelected?: boolean
  onSelect?: (findingId: string) => void
}

export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  onAccept,
  onReject,
  onManualEdit,
  onViewGuideline,
  isSelected = false,
  onSelect,
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(finding.manualReplacement || finding.suggestedCorrection)

  const handleSaveManual = () => {
    onManualEdit(finding.id, editText)
    setIsEditing(false)
  }

  const severityBadgeVariant =
    finding.severity === 'critical'
      ? 'destructive'
      : finding.severity === 'warning'
      ? 'warning'
      : 'blue'

  return (
    <div
      onClick={() => onSelect?.(finding.id)}
      className={`rounded-lg border p-4 transition-all text-xs space-y-3 cursor-pointer ${
        isSelected
          ? 'ring-2 ring-blue-500 border-blue-500 shadow-md bg-blue-50/20'
          : finding.status === 'accepted' || finding.status === 'manual'
          ? 'bg-emerald-50/40 border-emerald-200'
          : finding.status === 'rejected'
          ? 'bg-slate-50 border-slate-200 opacity-60'
          : 'bg-white border-border/90 shadow-xs hover:border-slate-300'
      }`}
    >
      {/* Top Header: Category, Severity & AI Confidence */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={severityBadgeVariant} className="text-[10px] uppercase font-semibold">
            {finding.severity}
          </Badge>

          <span className="font-semibold text-slate-900">
            {finding.category}
          </span>

          <span className="text-[10px] text-slate-400 font-mono">
            {finding.confidence}% confidence
          </span>
        </div>

        {/* Status indicator if resolved */}
        {finding.status !== 'pending' && (
          <Badge
            variant={finding.status === 'rejected' ? 'secondary' : 'success'}
            className="text-[10px] gap-1"
          >
            {finding.status === 'rejected' ? (
              <>
                <XCircle className="w-3 h-3 text-slate-500" />
                <span>Dismissed</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>{finding.status === 'manual' ? 'Custom Applied' : 'Correction Applied'}</span>
              </>
            )}
          </Badge>
        )}
      </div>

      {/* Problematic Text (Red Callout) */}
      <div className="space-y-1">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Original Problematic Text
        </div>
        <div className="p-2.5 rounded-md bg-rose-50/80 border border-rose-200 text-rose-950 font-serif text-xs leading-relaxed flex items-start gap-2">
          <span className="text-rose-600 font-bold shrink-0">✕</span>
          <span className="line-through decoration-rose-400">"{finding.originalText}"</span>
        </div>
      </div>

      {/* Explanation of the Violation */}
      <p className="text-slate-600 leading-relaxed text-xs">
        {finding.explanation}
      </p>

      {/* Suggested Correction (Blue Callout) */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          <span className="flex items-center gap-1 text-blue-700">
            <Sparkles className="w-3 h-3 text-blue-600" />
            AI Recommended Correction
          </span>
          <button
            type="button"
            onClick={() => setIsEditing(!isEditing)}
            className="text-slate-500 hover:text-blue-600 flex items-center gap-1 normal-case font-medium text-[11px]"
          >
            <Edit3 className="w-3 h-3" />
            <span>{isEditing ? 'Cancel Edit' : 'Edit Manually'}</span>
          </button>
        </div>

        {!isEditing ? (
          <div className="p-2.5 rounded-md bg-blue-50/70 border border-blue-200 text-blue-950 text-xs font-medium flex items-start gap-2">
            <CornerDownRight className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
            <span>"{finding.manualReplacement || finding.suggestedCorrection}"</span>
          </div>
        ) : (
          <div className="space-y-2 p-2.5 rounded-md bg-slate-50 border border-blue-300">
            <textarea
              rows={2}
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="w-full text-xs p-2 rounded border border-input bg-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500"
            />
            <div className="flex justify-end gap-1.5">
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-[10px]"
                onClick={() => setIsEditing(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primaryBlue"
                size="sm"
                className="h-6 text-[10px]"
                onClick={handleSaveManual}
              >
                Apply Custom Text
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Supporting Brand Guideline Reference & Actions */}
      <div className="pt-2 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Supporting Guideline Link */}
        <button
          type="button"
          onClick={() => onViewGuideline(finding)}
          className="text-[11px] text-slate-500 hover:text-blue-600 flex items-center gap-1.5 transition-colors text-left"
        >
          <BookOpen className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          <span className="font-medium underline-offset-2 hover:underline truncate">
            {finding.supportingGuideline.code}: {finding.supportingGuideline.title}
          </span>
        </button>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-auto">
          {finding.status === 'pending' ? (
            <>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs text-slate-600 hover:text-rose-600 gap-1"
                onClick={(e) => {
                  e.stopPropagation()
                  onReject(finding.id)
                }}
              >
                <X className="w-3 h-3" />
                <span>Reject</span>
              </Button>
              <Button
                variant="primaryBlue"
                size="sm"
                className="h-7 text-xs gap-1 font-semibold"
                onClick={(e) => {
                  e.stopPropagation()
                  onAccept(finding.id)
                }}
              >
                <Check className="w-3 h-3" />
                <span>Apply Fix</span>
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-[11px] text-slate-500"
              onClick={() => onAccept(finding.id)}
            >
              Re-evaluate
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
