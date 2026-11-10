import React, { useEffect, useState } from 'react'
import {
  FileSearch,
  BookOpen,
  SpellCheck,
  MessageSquare,
  Scale,
  FileCheck2,
  CheckCircle2,
  Loader2,
  Sparkles,
} from 'lucide-react'

interface AnalysisProgressOverlayProps {
  isOpen: boolean
  onComplete: () => void
}

const analysisStages = [
  { id: 1, label: 'Extracting content', icon: FileSearch, detail: 'Tokenizing body copy, paragraphs, and headlines...' },
  { id: 2, label: 'Loading approved brand knowledge', icon: BookOpen, detail: 'Syncing NovaPay vector ruleset (412 embeddings)...' },
  { id: 3, label: 'Checking brand terminology', icon: SpellCheck, detail: 'Cross-referencing approved glossary and deprecated terms...' },
  { id: 4, label: 'Evaluating tone and messaging', icon: MessageSquare, detail: 'Calibrating collaborative tone against institutional voice...' },
  { id: 5, label: 'Checking claims and facts', icon: Scale, detail: 'Auditing statutory disclosures, SLA guarantees, and claims...' },
  { id: 6, label: 'Preparing compliance report', icon: FileCheck2, detail: 'Compiling findings, confidence metrics, and suggested diffs...' },
]

export const AnalysisProgressOverlay: React.FC<AnalysisProgressOverlayProps> = ({
  isOpen,
  onComplete,
}) => {
  const [currentStage, setCurrentStage] = useState(0)
  const [progressPercent, setProgressPercent] = useState(10)

  useEffect(() => {
    if (!isOpen) {
      setCurrentStage(0)
      setProgressPercent(10)
      return
    }

    // Step through each of the 6 stages realistically
    const stageDuration = 380 // ms per stage
    const interval = setInterval(() => {
      setCurrentStage((prev) => {
        if (prev < analysisStages.length - 1) {
          const next = prev + 1
          setProgressPercent(Math.min(100, Math.round(((next + 1) / analysisStages.length) * 100)))
          return next
        } else {
          clearInterval(interval)
          setTimeout(() => {
            onComplete()
          }, 350)
          return prev
        }
      })
    }, stageDuration)

    return () => clearInterval(interval)
  }, [isOpen, onComplete])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl border border-slate-200 p-6 space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 border border-blue-200 flex items-center justify-center mx-auto shadow-sm">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Running Brand Governance Audit
            </h3>
            <p className="text-xs text-slate-500">
              Evaluating marketing draft against NovaPay Brand Guidelines v2.4
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
            <span>Overall Progress</span>
            <span className="font-mono text-blue-600">{progressPercent}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden shadow-inner">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-600 to-blue-500 transition-all duration-300 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* 6 Stages Checklist */}
        <div className="space-y-2.5 pt-1">
          {analysisStages.map((stage, idx) => {
            const Icon = stage.icon
            const isCompleted = idx < currentStage
            const isCurrent = idx === currentStage
            const isUpcoming = idx > currentStage

            return (
              <div
                key={stage.id}
                className={`flex items-center gap-3 p-2.5 rounded-lg border transition-all text-xs ${
                  isCurrent
                    ? 'border-blue-300 bg-blue-50/60 text-blue-950 shadow-xs'
                    : isCompleted
                    ? 'border-slate-100 bg-slate-50/70 text-slate-700'
                    : 'border-transparent text-slate-400 opacity-50'
                }`}
              >
                <div className="shrink-0">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  ) : (
                    <Icon className="w-4 h-4 text-slate-300" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="font-semibold flex items-center gap-1.5">
                    <span>{idx + 1}. {stage.label}</span>
                  </div>
                  {isCurrent && (
                    <div className="text-[11px] text-blue-600/90 animate-pulse mt-0.5 truncate">
                      {stage.detail}
                    </div>
                  )}
                </div>

                {isCompleted && (
                  <span className="text-[10px] font-mono font-medium text-emerald-600 shrink-0">
                    Done
                  </span>
                )}
              </div>
            )
          })}
        </div>

        <p className="text-[11px] text-center text-slate-400 italic">
          Simulated deterministic rule execution in compliance test mode
        </p>
      </div>
    </div>
  )
}
