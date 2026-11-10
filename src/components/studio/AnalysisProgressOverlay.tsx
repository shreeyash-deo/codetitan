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
  workspaceName?: string
}

const analysisStages = [
  { id: 1, label: 'Extracting content', icon: FileSearch, detail: 'Tokenizing body copy, paragraphs, and headlines...' },
  { id: 2, label: 'Loading approved brand knowledge', icon: BookOpen, detail: 'Syncing approved brand rules and compliance policies...' },
  { id: 3, label: 'Checking brand terminology', icon: SpellCheck, detail: 'Cross-referencing approved glossary and deprecated terms...' },
  { id: 4, label: 'Evaluating tone and messaging', icon: MessageSquare, detail: 'Calibrating collaborative tone against brand voice...' },
  { id: 5, label: 'Checking claims and facts', icon: Scale, detail: 'Auditing statutory disclosures, SLA guarantees, and claims...' },
  { id: 6, label: 'Preparing compliance report', icon: FileCheck2, detail: 'Compiling findings, confidence metrics, and suggested diffs...' },
]

export const AnalysisProgressOverlay: React.FC<AnalysisProgressOverlayProps> = ({
  isOpen,
  onComplete,
  workspaceName,
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
              {workspaceName
                ? `Evaluating marketing draft against ${workspaceName} approved guidelines`
                : 'Evaluating marketing draft against active approved brand guidelines'}
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
              className="h-full bg-blue-600 transition-all duration-300 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Stages Checklist */}
        <div className="space-y-2.5">
          {analysisStages.map((stage, idx) => {
            const Icon = stage.icon
            const isCompleted = idx < currentStage
            const isCurrent = idx === currentStage

            return (
              <div
                key={stage.id}
                className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                  isCurrent
                    ? 'border-blue-300 bg-blue-50/60 text-blue-900'
                    : isCompleted
                    ? 'border-slate-200 bg-slate-50/40 text-slate-700'
                    : 'border-transparent text-slate-400 opacity-60'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`p-1.5 rounded-md ${
                      isCurrent
                        ? 'bg-blue-600 text-white'
                        : isCompleted
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-slate-100 text-slate-400'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0">
                    <span className="font-semibold block truncate">{stage.label}</span>
                    <span className="text-[10px] text-slate-500 block truncate">
                      {stage.detail}
                    </span>
                  </div>
                </div>

                <div className="shrink-0 ml-2">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-slate-300" />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
