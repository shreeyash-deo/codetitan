import React, { useState } from 'react'
import type { PendingCandidateRule, ApprovedRule } from '@/types/guidelines'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Sparkles,
  Check,
  X,
  Edit2,
  FileText,
  Clock,
  ShieldAlert,
  AlertTriangle,
  CheckCheck,
  CheckCircle2,
  Info,
} from 'lucide-react'

interface PendingExtractionTabProps {
  candidates: PendingCandidateRule[]
  onApproveCandidate: (candidateId: string) => void
  onRejectCandidate: (candidateId: string) => void
  onEditCandidate: (candidate: PendingCandidateRule) => void
  onApproveAllHighConfidence?: () => void
}

export const PendingExtractionTab: React.FC<PendingExtractionTabProps> = ({
  candidates,
  onApproveCandidate,
  onRejectCandidate,
  onEditCandidate,
  onApproveAllHighConfidence,
}) => {
  const [filterCategory, setFilterCategory] = useState<string>('all')

  const filteredCandidates = candidates.filter((c) => {
    if (filterCategory === 'all') return true
    return c.category.toLowerCase() === filterCategory.toLowerCase()
  })

  return (
    <div className="space-y-6">
      {/* Important Human-in-the-Loop Governance Notice */}
      <div className="p-4 rounded-xl bg-blue-50/50 border border-blue-200/90 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <span>Authorised Human-in-the-Loop Governance Required</span>
              <Badge variant="blue" className="text-[10px]">
                Policy Guard
              </Badge>
            </h4>
            <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
              BrandShield AI extracts candidate rules from uploaded PDFs and DOCX manuals, but <strong className="text-slate-900">never automatically publishes them</strong>. Only rules explicitly approved by a designated Brand Lead become authoritative guidelines.
            </p>
          </div>
        </div>

        {candidates.length > 0 && onApproveAllHighConfidence && (
          <Button
            variant="primaryBlue"
            size="sm"
            onClick={onApproveAllHighConfidence}
            className="text-xs gap-1.5 shrink-0 self-start sm:self-auto font-semibold"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            <span>Approve High Confidence (&gt;90%)</span>
          </Button>
        )}
      </div>

      {/* Filter and Count Bar */}
      <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-border shadow-xs">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {['all', 'Brand Facts', 'Terminology', 'Claims & Restrictions', 'Brand Voice', 'Visual Identity'].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0 ${
                filterCategory === cat
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <span>{cat === 'all' ? 'All Pending' : cat}</span>
              {cat === 'all' && (
                <span className="ml-1.5 text-[10px] bg-slate-700 text-white px-1.5 py-0.2 rounded-full">
                  {candidates.length}
                </span>
              )}
            </button>
          ))}
        </div>

        <span className="text-xs text-slate-400 hidden sm:inline">
          {candidates.length} candidate rules awaiting review
        </span>
      </div>

      {/* Candidates Queue */}
      {filteredCandidates.length === 0 ? (
        <Card className="p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">
            Extraction Review Queue is Empty
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            All candidate rules extracted from source documentation have been evaluated and approved into authoritative brand knowledge.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredCandidates.map((candidate) => (
            <Card
              key={candidate.id}
              className="p-5 hover:border-slate-300 transition-all shadow-xs space-y-3"
            >
              {/* Header: Category, Subcategory, Confidence & Source Citation */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-2.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="blue" className="text-[10px]">
                    {candidate.category}
                  </Badge>
                  <span className="text-xs font-medium text-slate-600">
                    • {candidate.subCategory}
                  </span>
                  <Badge
                    variant={candidate.suggestedEnforcement === 'Strict' ? 'default' : 'neutral'}
                    className="text-[10px]"
                  >
                    Suggested: {candidate.suggestedEnforcement}
                  </Badge>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    <Sparkles className="w-3 h-3 text-blue-600" />
                    {candidate.confidence}% AI Confidence
                  </span>
                  <span className="text-[11px] text-slate-400">
                    Extracted {candidate.dateExtracted}
                  </span>
                </div>
              </div>

              {/* Title & Extracted Content */}
              <div className="space-y-2">
                <h4 className="text-sm font-bold text-slate-900">
                  {candidate.title}
                </h4>

                <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-800 leading-relaxed font-sans">
                  "{candidate.extractedText}"
                </div>

                <div className="p-2.5 rounded-md bg-blue-50/50 border border-blue-100 text-[11px] text-slate-600 flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-blue-600 mt-0.5 shrink-0" />
                  <div>
                    <strong className="text-blue-900">Extraction Context: </strong>
                    {candidate.rationale}
                  </div>
                </div>
              </div>

              {/* Footer: Source Document Citation & Action Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono text-[11px]">
                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-semibold text-slate-700">{candidate.sourceDocument}</span>
                  <span className="text-slate-400">({candidate.sourceSection})</span>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 gap-1"
                    onClick={() => onRejectCandidate(candidate.id)}
                  >
                    <X className="w-3 h-3" />
                    <span>Reject</span>
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs gap-1"
                    onClick={() => onEditCandidate(candidate)}
                  >
                    <Edit2 className="w-3 h-3" />
                    <span>Edit & Refine</span>
                  </Button>

                  <Button
                    variant="primaryBlue"
                    size="sm"
                    className="h-8 text-xs gap-1 font-semibold shadow-xs"
                    onClick={() => onApproveCandidate(candidate.id)}
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Approve Rule</span>
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
