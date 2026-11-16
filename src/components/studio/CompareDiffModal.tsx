import React, { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  X,
  GitCompare,
  Copy,
  Check,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Layers,
} from 'lucide-react'
import { reviewService } from '@/services/reviewService'
import type {
  ContentVersionSummary,
  VersionComparison,
} from '@/types/version'

interface CompareDiffModalProps {
  originalContent?: string
  correctedContent?: string
  isOpen: boolean
  onClose: () => void
  scoreBefore?: number
  scoreAfter?: number
  reviewId?: string | number
  currentVersionNumber?: number
  versions?: ContentVersionSummary[]
  initialSourceVersion?: number
  initialTargetVersion?: number
}

export const CompareDiffModal: React.FC<CompareDiffModalProps> = ({
  originalContent = '',
  correctedContent = '',
  isOpen,
  onClose,
  scoreBefore = 100,
  scoreAfter = 100,
  reviewId,
  currentVersionNumber = 1,
  versions: propVersions,
  initialSourceVersion,
  initialTargetVersion,
}) => {
  const [copiedTarget, setCopiedTarget] = useState(false)
  const [copiedSource, setCopiedSource] = useState(false)
  const [versionsList, setVersionsList] = useState<ContentVersionSummary[]>(propVersions || [])
  const [sourceVersionNum, setSourceVersionNum] = useState<number>(initialSourceVersion || 1)
  const [targetVersionNum, setTargetVersionNum] = useState<number>(initialTargetVersion || currentVersionNumber || 1)
  const [sourceContent, setSourceContent] = useState<string>(originalContent || '')
  const [targetContent, setTargetContent] = useState<string>(correctedContent || '')
  const [comparison, setComparison] = useState<VersionComparison | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [diffViewMode, setDiffViewMode] = useState<'side-by-side' | 'unified'>('side-by-side')
  const [activeTab, setActiveTab] = useState<'text' | 'findings'>('text')

  // Synchronize when initial props change
  useEffect(() => {
    if (initialSourceVersion) setSourceVersionNum(initialSourceVersion)
    if (initialTargetVersion) setTargetVersionNum(initialTargetVersion)
  }, [initialSourceVersion, initialTargetVersion])

  useEffect(() => {
    if (propVersions && propVersions.length > 0) {
      setVersionsList(propVersions)
    }
  }, [propVersions])

  // Load versions if reviewId is available
  useEffect(() => {
    if (!isOpen || !reviewId) return
    const fetchVersions = async () => {
      try {
        const list = await reviewService.getVersions(reviewId)
        if (list && list.length > 0) {
          setVersionsList(list)
          if (!initialSourceVersion) {
            setSourceVersionNum(list[0].versionNumber)
          }
          if (!initialTargetVersion) {
            const latest = list[list.length - 1].versionNumber
            setTargetVersionNum(currentVersionNumber || latest)
          }
        }
      } catch (err) {
        console.error('Failed to load version history:', err)
      }
    }
    fetchVersions()
  }, [isOpen, reviewId, currentVersionNumber, initialSourceVersion, initialTargetVersion])

  // Load comparison and version snapshots whenever source or target version changes
  useEffect(() => {
    if (!isOpen || !reviewId) {
      setComparison(null)
      return
    }

    const fetchComparisonAndSnapshots = async () => {
      setIsLoading(true)
      try {
        const [res, srcDetail, tgtDetail] = await Promise.all([
          reviewService.compareVersions(reviewId, sourceVersionNum, targetVersionNum),
          reviewService.getVersionDetail(reviewId, sourceVersionNum).catch(() => null),
          reviewService.getVersionDetail(reviewId, targetVersionNum).catch(() => null),
        ])
        setComparison(res)
        if (srcDetail?.content !== undefined) {
          setSourceContent(srcDetail.content)
        } else if (res?.sourceContent) {
          setSourceContent(res.sourceContent)
        }
        if (tgtDetail?.content !== undefined) {
          setTargetContent(tgtDetail.content)
        } else if (res?.targetContent) {
          setTargetContent(res.targetContent)
        }
      } catch (err) {
        console.error('Failed to compare versions:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchComparisonAndSnapshots()
  }, [isOpen, reviewId, sourceVersionNum, targetVersionNum])

  if (!isOpen) return null

  const handleCopyTarget = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedTarget(true)
    setTimeout(() => setCopiedTarget(false), 2000)
  }

  const handleCopySource = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedSource(true)
    setTimeout(() => setCopiedSource(false), 2000)
  }

  // Derive scores and content
  const activeScoreBefore = comparison ? comparison.scoreBefore : scoreBefore
  const activeScoreAfter = comparison ? comparison.scoreAfter : scoreAfter
  const scoreDelta = comparison ? comparison.scoreDelta : activeScoreAfter - activeScoreBefore

  const displaySourceContent = sourceContent || comparison?.sourceContent || originalContent || ''
  const displayTargetContent = targetContent || comparison?.targetContent || correctedContent || ''

  const hasDiffChanges = (comparison?.textDiff || []).some((h) => {
    const type = h.changeType || (h as any).change_type || 'unchanged'
    return type === 'added' || type === 'removed'
  })

  const isIdentical =
    sourceVersionNum === targetVersionNum ||
    (!hasDiffChanges && (comparison ? true : displaySourceContent.trim() === displayTargetContent.trim()))

  return (
    <div className="fixed inset-0 z-[60] overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-5xl rounded-xl bg-white shadow-2xl border border-border p-6 space-y-5 animate-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-border gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <GitCompare className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900">
                    Content Version History & Comparison
                  </h3>
                  {versionsList.length > 1 && (
                    <Badge variant="outline" className="text-[10px] gap-1">
                      <Layers className="w-3 h-3 text-blue-600" />
                      {versionsList.length} Versions
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  Compare content revisions, verify compliance score delta, and track resolved violations.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Score Delta Pill */}
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold">
                <span className="text-slate-600">Score:</span>
                <span className="text-rose-600">{activeScoreBefore}</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-emerald-600">{activeScoreAfter}</span>
                <span
                  className={`ml-1 text-[11px] px-1.5 py-0.5 rounded-md font-bold flex items-center gap-0.5 ${
                    scoreDelta > 0
                      ? 'bg-emerald-100 text-emerald-800'
                      : scoreDelta < 0
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {scoreDelta > 0 ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : scoreDelta < 0 ? (
                    <TrendingDown className="w-3 h-3" />
                  ) : null}
                  {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta} pts
                </span>
              </div>

              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Version Selector Bar (if multiple versions exist) */}
          {versionsList.length > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-4 p-3 bg-slate-50/80 border border-slate-200 rounded-lg text-xs">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-slate-700">Source:</span>
                  <select
                    value={sourceVersionNum}
                    onChange={(e) => setSourceVersionNum(Number(e.target.value))}
                    className="border border-slate-300 rounded px-2 py-1 bg-white font-medium text-slate-800 text-xs shadow-xs focus:ring-1 focus:ring-blue-500"
                  >
                    {versionsList.map((v) => (
                      <option key={v.id} value={v.versionNumber}>
                        v{v.versionNumber} ({v.complianceScore} pts) - {v.changeDescription || 'Snapshot'}
                      </option>
                    ))}
                  </select>
                  {sourceVersionNum < targetVersionNum ? (
                    <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-600 border-slate-300 font-semibold">
                      Older
                    </Badge>
                  ) : sourceVersionNum > targetVersionNum ? (
                    <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200 font-semibold">
                      Newer
                    </Badge>
                  ) : null}
                </div>

                <ArrowRight className="w-4 h-4 text-slate-400" />

                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-slate-700">Target:</span>
                  <select
                    value={targetVersionNum}
                    onChange={(e) => setTargetVersionNum(Number(e.target.value))}
                    className="border border-slate-300 rounded px-2 py-1 bg-white font-medium text-slate-800 text-xs shadow-xs focus:ring-1 focus:ring-blue-500"
                  >
                    {versionsList.map((v) => (
                      <option key={v.id} value={v.versionNumber}>
                        v{v.versionNumber} ({v.complianceScore} pts) - {v.changeDescription || 'Snapshot'}
                      </option>
                    ))}
                  </select>
                  {targetVersionNum > sourceVersionNum ? (
                    <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200 font-semibold">
                      Newer
                    </Badge>
                  ) : targetVersionNum < sourceVersionNum ? (
                    <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-600 border-slate-300 font-semibold">
                      Older
                    </Badge>
                  ) : null}
                </div>
              </div>

              {/* View Tabs */}
              <div className="flex items-center gap-2">
                <div className="flex border border-slate-300 rounded-md overflow-hidden bg-white">
                  <button
                    onClick={() => setActiveTab('text')}
                    className={`px-3 py-1 font-medium transition-colors ${
                      activeTab === 'text'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Text Diff
                  </button>
                  <button
                    onClick={() => setActiveTab('findings')}
                    className={`px-3 py-1 font-medium transition-colors flex items-center gap-1 ${
                      activeTab === 'findings'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Findings Delta
                    {comparison?.findingsDelta && (
                      <span className="text-[10px] bg-slate-100 text-slate-800 px-1 rounded-full">
                        {comparison.findingsDelta.resolved.length} resolved
                      </span>
                    )}
                  </button>
                </div>

                {activeTab === 'text' && comparison?.textDiff && comparison.textDiff.length > 0 && (
                  <div className="flex border border-slate-300 rounded-md overflow-hidden bg-white text-[11px]">
                    <button
                      onClick={() => setDiffViewMode('side-by-side')}
                      className={`px-2 py-1 font-medium ${
                        diffViewMode === 'side-by-side' ? 'bg-slate-800 text-white' : 'text-slate-600'
                      }`}
                    >
                      Side by Side
                    </button>
                    <button
                      onClick={() => setDiffViewMode('unified')}
                      className={`px-2 py-1 font-medium ${
                        diffViewMode === 'unified' ? 'bg-slate-800 text-white' : 'text-slate-600'
                      }`}
                    >
                      Unified
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab Content */}
          {activeTab === 'text' && (
            <>
              {/* Notice / Banner when no differences found */}
              {isIdentical && (
                <div className="p-3.5 bg-amber-50/90 border border-amber-300 rounded-lg text-xs text-amber-900 flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0" />
                  <div>
                    <span className="font-bold">No differences found.</span>{' '}
                    <span className="text-amber-800">
                      {sourceVersionNum === targetVersionNum
                        ? `Version ${sourceVersionNum} is being compared against itself.`
                        : `Version ${sourceVersionNum} and Version ${targetVersionNum} have identical content.`}
                    </span>
                  </div>
                </div>
              )}

              {diffViewMode === 'unified' && comparison?.textDiff ? (
                <div className="border border-slate-200 rounded-lg p-4 font-mono text-xs bg-slate-900 text-slate-100 max-h-[380px] overflow-y-auto space-y-1">
                  {comparison.textDiff.map((hunk, idx) => {
                    const type = hunk.changeType || (hunk as any).change_type || 'unchanged'
                    return (
                      <div
                        key={idx}
                        className={`p-1.5 rounded whitespace-pre-wrap leading-relaxed ${
                          type === 'added'
                            ? 'bg-emerald-950/80 text-emerald-300 border-l-2 border-emerald-500'
                            : type === 'removed'
                            ? 'bg-rose-950/80 text-rose-300 line-through border-l-2 border-rose-500'
                            : 'text-slate-300'
                        }`}
                      >
                        <span className="mr-2 select-none opacity-60 font-bold">
                          {type === 'added' ? '+' : type === 'removed' ? '-' : ' '}
                        </span>
                        {hunk.content}
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Source Version Draft */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-rose-700 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-rose-500" />
                        {versionsList.length > 1
                          ? `Version ${sourceVersionNum} Snapshot`
                          : 'Original Submitted Draft'}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="text-[11px] text-slate-400 font-mono">
                          {displaySourceContent.length} chars
                        </span>
                        <button
                          onClick={() => handleCopySource(displaySourceContent)}
                          className="text-[11px] text-slate-600 hover:text-blue-600 hover:underline flex items-center gap-1"
                        >
                          {copiedSource ? (
                            <Check className="w-3 h-3 text-emerald-600" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                          <span>{copiedSource ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-rose-50/40 border border-rose-200/80 text-xs font-serif text-slate-800 leading-relaxed min-h-[260px] max-h-[360px] overflow-y-auto whitespace-pre-wrap">
                      {!isIdentical && comparison?.textDiff && comparison.textDiff.length > 0 ? (
                        comparison.textDiff
                          .filter((h) => {
                            const type = h.changeType || (h as any).change_type || 'unchanged'
                            return type !== 'added'
                          })
                          .map((h, idx) => {
                            const type = h.changeType || (h as any).change_type || 'unchanged'
                            if (type === 'removed') {
                              return (
                                <span
                                  key={idx}
                                  className="bg-rose-100 text-rose-900 border-b border-rose-400 font-medium px-1 py-0.5 rounded line-through decoration-rose-500"
                                >
                                  {h.content}{' '}
                                </span>
                              )
                            }
                            return <span key={idx}>{h.content} </span>
                          })
                      ) : (
                        displaySourceContent
                      )}
                    </div>
                  </div>

                  {/* Target Version Draft */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-xs font-semibold flex items-center gap-1.5 ${
                          isIdentical ? 'text-amber-700' : 'text-emerald-700'
                        }`}
                      >
                        <span
                          className={`w-2 h-2 rounded-full ${
                            isIdentical ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}
                        />
                        {versionsList.length > 1
                          ? `Version ${targetVersionNum} Draft`
                          : isIdentical
                          ? 'Working Draft (Unmodified)'
                          : 'Governance-Remediated Draft'}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="text-[11px] text-slate-400 font-mono">
                          {displayTargetContent.length} chars
                        </span>
                        <button
                          onClick={() => handleCopyTarget(displayTargetContent)}
                          className="text-[11px] text-blue-600 hover:underline flex items-center gap-1"
                        >
                          {copiedTarget ? (
                            <Check className="w-3 h-3 text-emerald-600" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                          <span>{copiedTarget ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                    </div>
                    <div
                      className={`p-4 rounded-lg border text-xs font-serif text-slate-800 leading-relaxed min-h-[260px] max-h-[360px] overflow-y-auto whitespace-pre-wrap ${
                        isIdentical
                          ? 'bg-amber-50/30 border-amber-200/70'
                          : 'bg-emerald-50/40 border-emerald-200/80'
                      }`}
                    >
                      {!isIdentical && comparison?.textDiff && comparison.textDiff.length > 0 ? (
                        comparison.textDiff
                          .filter((h) => {
                            const type = h.changeType || (h as any).change_type || 'unchanged'
                            return type !== 'removed'
                          })
                          .map((h, idx) => {
                            const type = h.changeType || (h as any).change_type || 'unchanged'
                            if (type === 'added') {
                              return (
                                <span
                                  key={idx}
                                  className="bg-emerald-100 text-emerald-900 border-b border-emerald-400 font-medium px-1 py-0.5 rounded"
                                >
                                  {h.content}{' '}
                                </span>
                              )
                            }
                            return <span key={idx}>{h.content} </span>
                          })
                      ) : (
                        displayTargetContent
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Findings Delta Tab */}
          {activeTab === 'findings' && comparison?.findingsDelta && (
            <div className="space-y-4 max-h-[380px] overflow-y-auto pr-1">
              {/* Resolved Findings */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    Resolved Violations ({comparison.findingsDelta.resolved.length})
                  </h4>
                  <span className="text-[11px] text-emerald-600 font-medium">
                    Present in v{sourceVersionNum}, remediated in v{targetVersionNum}
                  </span>
                </div>
                {comparison.findingsDelta.resolved.length === 0 ? (
                  <p className="text-xs text-slate-400 italic bg-slate-50 p-3 rounded border border-dashed border-slate-200">
                    No violations were resolved between these versions.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {comparison.findingsDelta.resolved.map((f) => (
                      <div
                        key={f.id}
                        className="p-3 bg-emerald-50/60 border border-emerald-200 rounded-lg text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-emerald-900">{f.category}</span>
                          <Badge variant="outline" className="text-[10px] bg-emerald-100 text-emerald-800 border-emerald-300">
                            Remediated
                          </Badge>
                        </div>
                        <p className="text-slate-700 italic">"{f.originalText}"</p>
                        {f.suggestedCorrection && (
                          <p className="text-emerald-700 font-medium">
                            Correction: "{f.suggestedCorrection}"
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Newly Introduced Findings */}
              {comparison.findingsDelta.new.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-rose-800 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      Newly Introduced Violations ({comparison.findingsDelta.new.length})
                    </h4>
                    <span className="text-[11px] text-rose-600 font-medium">
                      Introduced in v{targetVersionNum}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {comparison.findingsDelta.new.map((f) => (
                      <div
                        key={f.id}
                        className="p-3 bg-rose-50/60 border border-rose-200 rounded-lg text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-rose-900">{f.category}</span>
                          <Badge variant="destructive" className="text-[10px]">
                            {f.severity}
                          </Badge>
                        </div>
                        <p className="text-slate-700 italic">"{f.originalText}"</p>
                        <p className="text-rose-700">{f.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Persistent Findings */}
              {comparison.findingsDelta.persistent.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-amber-800 flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-amber-600" />
                    Persistent Violations ({comparison.findingsDelta.persistent.length})
                  </h4>
                  <div className="space-y-2">
                    {comparison.findingsDelta.persistent.map((f) => (
                      <div
                        key={f.id}
                        className="p-3 bg-amber-50/50 border border-amber-200 rounded-lg text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-amber-900">{f.category}</span>
                          <Badge variant="outline" className="text-[10px] bg-amber-100 text-amber-800 border-amber-300">
                            Unresolved
                          </Badge>
                        </div>
                        <p className="text-slate-700 italic">"{f.originalText}"</p>
                        <p className="text-amber-700">{f.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-border">
            <span className="text-xs text-slate-500">
              {isIdentical
                ? 'Working content has not been modified. Apply suggested corrections or edit text to remediate violations.'
                : 'Compliant copy remediates identified brand and regulatory findings.'}
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
