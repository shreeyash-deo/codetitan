import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { StudioCategory, StrictnessLevel } from '@/types/reviewStudio'
import {
  Sliders,
  CheckCircle2,
  BookOpen,
  Shield,
  FileCheck2,
  Info,
  Check,
} from 'lucide-react'

interface ReviewConfigPanelProps {
  activeCategories: StudioCategory[]
  toggleCategory: (cat: StudioCategory) => void
  strictness: StrictnessLevel
  setStrictness: (level: StrictnessLevel) => void
  activeGuidelines: string[]
  toggleGuideline: (id: string) => void
  contentLength: number
  wordCount: number
  status: 'ready' | 'analyzing' | 'completed'
}

const availableGuidelines = [
  { id: 'bg-identity', name: 'NovaPay Master Identity v2.4', count: 18, desc: 'Logo isolation, marks, and approved palettes' },
  { id: 'bg-voice', name: 'Tone of Voice & Lexicon Rules', count: 24, desc: 'Institutional dignity, banned buzzwords' },
  { id: 'bg-statutory', name: 'Statutory Claims & Disclaimers', count: 12, desc: 'FCA & FTC advertising disclosures' },
  { id: 'bg-risk', name: 'Product Warranties & Fraud Terms', count: 9, desc: 'SLA guarantees, liability boundaries' },
]

const availableCategories: { id: StudioCategory; label: string; desc: string }[] = [
  { id: 'Tone inconsistency', label: 'Tone inconsistency', desc: 'Detects colloquial or aggressive rhetoric' },
  { id: 'Incorrect terminology', label: 'Incorrect terminology', desc: 'Flags deprecated product names' },
  { id: 'Unsupported claims', label: 'Unsupported claims', desc: 'Validates superlatives & statistics' },
  { id: 'Incorrect product facts', label: 'Incorrect product facts', desc: 'Audits feature capabilities' },
  { id: 'Visual brand inconsistency', label: 'Visual brand inconsistency', desc: 'Checks contrast, clearspace & assets' },
]

export const ReviewConfigPanel: React.FC<ReviewConfigPanelProps> = ({
  activeCategories,
  toggleCategory,
  strictness,
  setStrictness,
  activeGuidelines,
  toggleGuideline,
  contentLength,
  wordCount,
  status,
}) => {
  return (
    <Card className="h-full border-border/80 shadow-xs flex flex-col justify-between">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-600" />
              <span>Review Configuration</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Customize enforcement criteria and active vector rules
            </CardDescription>
          </div>

          <Badge
            variant={
              status === 'completed'
                ? 'success'
                : status === 'analyzing'
                ? 'blue'
                : 'secondary'
            }
            className="text-[10px] uppercase font-mono"
          >
            {status === 'completed'
              ? 'Audit Ready'
              : status === 'analyzing'
              ? 'Analyzing...'
              : 'Configured'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-5 flex-1 overflow-y-auto">
        {/* Strictness Selector */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-800">
              Enforcement Strictness
            </label>
            <span className="text-[11px] text-blue-600 font-medium capitalize">
              {strictness} Mode
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'advisory', label: 'Advisory', desc: 'Suggestions only' },
              { id: 'standard', label: 'Standard', desc: 'Default enterprise' },
              { id: 'strict', label: 'Strict', desc: 'Zero tolerance' },
            ].map((lvl) => (
              <button
                key={lvl.id}
                type="button"
                onClick={() => setStrictness(lvl.id as StrictnessLevel)}
                className={`p-2 rounded-lg border text-left transition-all ${
                  strictness === lvl.id
                    ? 'border-blue-600 bg-blue-50/70 text-blue-900 ring-1 ring-blue-500/20'
                    : 'border-border bg-white text-slate-700 hover:border-slate-300'
                }`}
              >
                <div className="font-semibold text-xs">{lvl.label}</div>
                <div className="text-[10px] text-slate-500 truncate">{lvl.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Review Categories Toggles */}
        <div className="space-y-2 pt-1 border-t border-border/60">
          <label className="text-xs font-semibold text-slate-800 flex items-center justify-between">
            <span>Audit Categories</span>
            <span className="text-[11px] text-slate-400 font-normal">
              {activeCategories.length}/{availableCategories.length} active
            </span>
          </label>

          <div className="space-y-1.5">
            {availableCategories.map((cat) => {
              const isChecked = activeCategories.includes(cat.id)
              return (
                <div
                  key={cat.id}
                  onClick={() => toggleCategory(cat.id)}
                  className={`flex items-start justify-between p-2 rounded-md border cursor-pointer select-none transition-colors ${
                    isChecked
                      ? 'border-slate-200 bg-slate-50/70'
                      : 'border-transparent hover:bg-slate-50 opacity-60'
                  }`}
                >
                  <div className="text-xs">
                    <div className="font-medium text-slate-800">{cat.label}</div>
                    <div className="text-[10px] text-slate-400">{cat.desc}</div>
                  </div>

                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {}}
                    className="h-3.5 w-3.5 mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                </div>
              )
            })}
          </div>
        </div>

        {/* Active Brand Guidelines Checklist */}
        <div className="space-y-2 pt-1 border-t border-border/60">
          <label className="text-xs font-semibold text-slate-800 flex items-center justify-between">
            <span>Linked Brand Knowledge</span>
            <span className="text-[11px] text-emerald-600 font-medium">
              412 vectors indexed
            </span>
          </label>

          <div className="space-y-1.5">
            {availableGuidelines.map((gl) => {
              const isChecked = activeGuidelines.includes(gl.id)
              return (
                <div
                  key={gl.id}
                  onClick={() => toggleGuideline(gl.id)}
                  className={`flex items-center justify-between p-2 rounded-md border text-xs cursor-pointer select-none transition-colors ${
                    isChecked
                      ? 'border-blue-200 bg-blue-50/40 text-blue-950'
                      : 'border-slate-100 bg-white text-slate-600 opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate pr-2">
                    <BookOpen className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                    <span className="font-medium truncate">{gl.name}</span>
                  </div>
                  <Badge variant="neutral" className="text-[10px] shrink-0 font-mono">
                    {gl.count} rules
                  </Badge>
                </div>
              )
            })}
          </div>
        </div>

        {/* Document Stats / Telemetry */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 text-xs space-y-1.5">
          <div className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
            Document Telemetry
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600">
            <div>
              <span className="text-slate-400">Word Count:</span> {wordCount}
            </div>
            <div>
              <span className="text-slate-400">Tokens:</span> ~{Math.ceil(contentLength / 4)}
            </div>
            <div>
              <span className="text-slate-400">Language:</span> EN-US (Financial)
            </div>
            <div>
              <span className="text-slate-400">Est. Latency:</span> &lt;1.8s
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
