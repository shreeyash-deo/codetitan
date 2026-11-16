import React, { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  X,
  History,
  GitCompare,
  Clock,
  User,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Send,
  FileText,
  Copy,
  Check,
  Eye,
  ArrowRight,
  Layers,
  Sparkles,
  RefreshCw,
  Lock,
} from 'lucide-react'
import { reviewService } from '@/services/reviewService'
import { CompareDiffModal } from './CompareDiffModal'
import type {
  ContentVersionSummary,
  ContentVersionDetail,
} from '@/types/version'

interface VersionHistoryModalProps {
  reviewId?: string | number | null
  reviewTitle?: string
  currentVersionNumber?: number
  isOpen: boolean
  onClose: () => void
  onCompareVersions?: (sourceVersion: number, targetVersion: number) => void
}

export const VersionHistoryModal: React.FC<VersionHistoryModalProps> = ({
  reviewId,
  reviewTitle = 'Marketing Asset',
  currentVersionNumber = 1,
  isOpen,
  onClose,
  onCompareVersions,
}) => {
  const [versionsList, setVersionsList] = useState<ContentVersionSummary[]>([])
  const [selectedVersionNum, setSelectedVersionNum] = useState<number>(currentVersionNumber || 1)
  const [selectedVersionDetail, setSelectedVersionDetail] = useState<ContentVersionDetail | null>(null)
  const [isLoadingList, setIsLoadingList] = useState(false)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [copiedHash, setCopiedHash] = useState(false)
  const [copiedContent, setCopiedContent] = useState(false)

  // Compare selection state
  const [compareSourceNum, setCompareSourceNum] = useState<number>(1)
  const [compareTargetNum, setCompareTargetNum] = useState<number>(currentVersionNumber || 1)
  const [isCompareDiffOpen, setIsCompareDiffOpen] = useState(false)

  // Load versions list
  useEffect(() => {
    if (!isOpen || !reviewId) return
    const fetchList = async () => {
      setIsLoadingList(true)
      try {
        const list = await reviewService.getVersions(reviewId)
        if (list && list.length > 0) {
          setVersionsList(list)
          // Default selection to current or latest
          const latest = list[list.length - 1].versionNumber
          const defaultVer = currentVersionNumber || latest
          setSelectedVersionNum(defaultVer)
          setCompareSourceNum(list[0].versionNumber)
          setCompareTargetNum(defaultVer)
        }
      } catch (err) {
        console.error('Failed to load version history list:', err)
      } finally {
        setIsLoadingList(false)
      }
    }
    fetchList()
  }, [isOpen, reviewId, currentVersionNumber])

  // Load detail for selected version
  useEffect(() => {
    if (!isOpen || !reviewId || !selectedVersionNum) return
    const fetchDetail = async () => {
      setIsLoadingDetail(true)
      try {
        const detail = await reviewService.getVersionDetail(reviewId, selectedVersionNum)
        setSelectedVersionDetail(detail)
      } catch (err) {
        console.error(`Failed to load detail for version ${selectedVersionNum}:`, err)
      } finally {
        setIsLoadingDetail(false)
      }
    }
    fetchDetail()
  }, [isOpen, reviewId, selectedVersionNum])

  if (!isOpen) return null

  const handleCopy = (text: string, type: 'hash' | 'content') => {
    navigator.clipboard.writeText(text)
    if (type === 'hash') {
      setCopiedHash(true)
      setTimeout(() => setCopiedHash(false), 2000)
    } else {
      setCopiedContent(true)
      setTimeout(() => setCopiedContent(false), 2000)
    }
  }

  const handleLaunchCompare = () => {
    if (onCompareVersions) {
      onCompareVersions(compareSourceNum, compareTargetNum)
    } else {
      setIsCompareDiffOpen(true)
    }
  }

  const getStateBadge = (v: ContentVersionSummary) => {
    const state = v.versionState || (v.auditStatus === 'verified' ? 'audited' : 'saved_draft')
    switch (state) {
      case 'approved':
        return (
          <Badge variant="success" className="text-[10px] gap-1 px-1.5 py-0.5">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Approved
          </Badge>
        )
      case 'submitted':
        return (
          <Badge variant="blue" className="text-[10px] gap-1 px-1.5 py-0.5">
            <Send className="w-3 h-3 text-blue-600" />
            Submitted
          </Badge>
        )
      case 'changes_requested':
        return (
          <Badge variant="warning" className="text-[10px] gap-1 px-1.5 py-0.5">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Changes Requested
          </Badge>
        )
      case 'audited':
        return (
          <Badge variant="outline" className="text-[10px] gap-1 px-1.5 py-0.5 border-indigo-200 text-indigo-700 bg-indigo-50/60">
            <ShieldCheck className="w-3 h-3 text-indigo-600" />
            Audited
          </Badge>
        )
      default:
        return (
          <Badge variant="secondary" className="text-[10px] gap-1 px-1.5 py-0.5 text-slate-600">
            <FileText className="w-3 h-3 text-slate-500" />
            Saved Draft
          </Badge>
        )
    }
  }

  const getAuditStatusBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
            <ShieldCheck className="w-3 h-3 text-emerald-600" />
            Verified
          </span>
        )
      case 'degraded':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Degraded
          </span>
        )
      case 'rules_unavailable':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded">
            Incomplete
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded">
            {status}
          </span>
        )
    }
  }

  const formatTimestamp = (isoStr: string) => {
    try {
      const d = new Date(isoStr)
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoStr
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-3 sm:p-5">
        <div className="relative w-full max-w-6xl rounded-xl bg-white shadow-2xl border border-border p-5 sm:p-6 space-y-4 animate-in zoom-in-95 duration-150 max-h-[92vh] flex flex-col">
          {/* Modal Header */}
          <div className="flex items-start justify-between pb-4 border-b border-border gap-4 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                <History className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-lg font-bold text-slate-900 truncate">
                    Version History: {reviewTitle}
                  </h2>
                  <Badge variant="outline" className="text-[10px] gap-1">
                    <Layers className="w-3 h-3 text-blue-600" />
                    {versionsList.length} {versionsList.length === 1 ? 'Version' : 'Versions'}
                  </Badge>
                  {reviewId && (
                    <span className="text-xs text-slate-400 font-mono">
                      Review #{reviewId}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Immutable chronological audit snapshots. Inspect any past version and compare revisions.
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Compare Toolbar (if >= 2 versions exist) */}
          {versionsList.length >= 2 && (
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs shrink-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-slate-700 flex items-center gap-1">
                  <GitCompare className="w-3.5 h-3.5 text-blue-600" />
                  Compare Revisions:
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500 font-medium">Source:</span>
                  <select
                    value={compareSourceNum}
                    onChange={(e) => setCompareSourceNum(Number(e.target.value))}
                    className="border border-slate-300 rounded px-2 py-1 bg-white font-medium text-slate-800 text-xs shadow-xs focus:ring-1 focus:ring-blue-500"
                  >
                    {versionsList.map((v) => (
                      <option key={v.id} value={v.versionNumber}>
                        v{v.versionNumber} ({v.complianceScore} pts) - {v.changeDescription || 'Snapshot'}
                        {v.versionNumber < compareTargetNum ? ' (Older)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />

                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500 font-medium">Target:</span>
                  <select
                    value={compareTargetNum}
                    onChange={(e) => setCompareTargetNum(Number(e.target.value))}
                    className="border border-slate-300 rounded px-2 py-1 bg-white font-medium text-slate-800 text-xs shadow-xs focus:ring-1 focus:ring-blue-500"
                  >
                    {versionsList.map((v) => (
                      <option key={v.id} value={v.versionNumber}>
                        v{v.versionNumber} ({v.complianceScore} pts) - {v.changeDescription || 'Snapshot'}
                        {v.versionNumber > compareSourceNum ? ' (Newer)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <Button
                size="sm"
                variant="primaryBlue"
                className="h-7 text-xs font-semibold gap-1.5"
                onClick={handleLaunchCompare}
              >
                <GitCompare className="w-3.5 h-3.5" />
                <span>Open Version Diff</span>
              </Button>
            </div>
          )}

          {/* Main Content Area: 2 Columns */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1 min-h-0 overflow-hidden">
            {/* Left Column: Versions Timeline (5 cols) */}
            <div className="lg:col-span-5 flex flex-col min-h-0 border border-slate-200 rounded-lg overflow-hidden bg-slate-50/50">
              <div className="p-3 bg-slate-100/80 border-b border-slate-200 flex items-center justify-between text-xs font-bold text-slate-700 shrink-0">
                <span>Version Timeline</span>
                <span className="text-slate-500 font-normal">
                  {versionsList.length} saved {versionsList.length === 1 ? 'record' : 'records'}
                </span>
              </div>

              <div className="p-3 overflow-y-auto space-y-2.5 flex-1">
                {isLoadingList && (
                  <div className="flex items-center justify-center p-8 text-slate-400 gap-2 text-xs">
                    <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                    <span>Loading version history...</span>
                  </div>
                )}

                {!isLoadingList && versionsList.length === 0 && (
                  <div className="text-center p-8 text-slate-400 text-xs">
                    No version snapshots found for this review.
                  </div>
                )}

                {versionsList.map((v) => {
                  const verNum = v.versionNumber ?? (v as any).version_number ?? 1
                  const isSelected = selectedVersionNum === verNum
                  const isCurrent = v.isCurrent ?? (v as any).is_current ?? verNum === currentVersionNumber
                  const isOriginal = v.isOriginal ?? (v as any).is_original ?? verNum === 1
                  const changeDesc = v.changeDescription || (v as any).change_description || (isOriginal ? 'Initial Submission' : 'Content updated')
                  const createdAt = v.createdAt || (v as any).created_at || ''
                  const authorName = v.authorName || (v as any).author_name
                  const score = v.complianceScore ?? (v as any).compliance_score ?? 100
                  const auditStatus = v.auditStatus || (v as any).audit_status || 'verified'
                  const findingsCount = v.findingsCount ?? (v as any).findings_count ?? 0

                  return (
                    <div
                      key={v.id}
                      onClick={() => setSelectedVersionNum(verNum)}
                      className={`p-3 rounded-lg border transition-all cursor-pointer text-xs space-y-2 ${
                        isSelected
                          ? 'bg-white border-blue-500 shadow-md ring-1 ring-blue-500'
                          : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/80'
                      }`}
                    >
                      {/* Top Row: Version Number, State Badge, and Markers */}
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-sm text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 font-mono">
                            v{verNum}
                          </span>
                          {isCurrent && (
                            <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200 font-semibold">
                              Current Active
                            </Badge>
                          )}
                          {isOriginal && (
                            <Badge variant="outline" className="text-[10px] text-slate-600 border-slate-300">
                              Original
                            </Badge>
                          )}
                        </div>

                        {getStateBadge(v)}
                      </div>

                      {/* Description */}
                      <div className="font-medium text-slate-800 line-clamp-1">
                        {changeDesc}
                      </div>

                      {/* Metadata Row: Date & Author */}
                      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                        <span className="flex items-center gap-1 truncate">
                          <Clock className="w-3 h-3 text-slate-400 shrink-0" />
                          {formatTimestamp(createdAt)}
                        </span>
                        {authorName && (
                          <span className="flex items-center gap-1 text-slate-600 truncate font-medium">
                            <User className="w-3 h-3 text-slate-400 shrink-0" />
                            {authorName}
                          </span>
                        )}
                      </div>

                      {/* Metrics Pill Bar */}
                      <div className="flex items-center justify-between gap-2 pt-1 text-[11px]">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-slate-500">Score:</span>
                          <span
                            className={`font-bold ${
                              score >= 90
                                ? 'text-emerald-700'
                                : score >= 75
                                ? 'text-blue-700'
                                : 'text-amber-700'
                            }`}
                          >
                            {score}/100
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {getAuditStatusBadge(auditStatus)}
                          <span className="text-slate-400 font-mono text-[10px]">
                            {findingsCount} {findingsCount === 1 ? 'finding' : 'findings'}
                          </span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Right Column: Full Read-Only Version Inspector (7 cols) */}
            <div className="lg:col-span-7 flex flex-col min-h-0 border border-slate-200 rounded-lg overflow-hidden bg-white">
              {isLoadingDetail ? (
                <div className="flex-1 flex items-center justify-center p-12 text-slate-400 gap-2 text-xs">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                  <span>Loading snapshot details for v{selectedVersionNum}...</span>
                </div>
              ) : selectedVersionDetail ? (
                <div className="flex flex-col h-full overflow-hidden">
                  {/* Read-Only Banner */}
                  <div className="bg-amber-50 border-b border-amber-200 px-3.5 py-2 flex items-center justify-between gap-2 text-xs text-amber-900 shrink-0">
                    <div className="flex items-center gap-1.5 font-medium">
                      <Lock className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                      <span>Historical Snapshot (v{selectedVersionDetail.versionNumber}) — Read-Only & Immutable</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 text-[11px] gap-1 text-amber-800 hover:bg-amber-100"
                        onClick={() => handleCopy(selectedVersionDetail.content, 'content')}
                      >
                        {copiedContent ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedContent ? 'Copied' : 'Copy Content'}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Version Meta Summary Bar */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 bg-slate-50 border-b border-slate-200 text-xs shrink-0">
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Compliance Score</span>
                      <span className={`text-sm font-bold ${
                        (selectedVersionDetail.complianceScore ?? (selectedVersionDetail as any).compliance_score ?? 100) >= 90 ? 'text-emerald-700' : 'text-blue-700'
                      }`}>
                        {selectedVersionDetail.complianceScore ?? (selectedVersionDetail as any).compliance_score ?? 100}/100
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Audit Status</span>
                      <div className="mt-0.5">
                        {getAuditStatusBadge(selectedVersionDetail.auditStatus || (selectedVersionDetail as any).audit_status || 'verified')}
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Violations</span>
                      <span className="text-xs font-semibold text-slate-800 mt-0.5 block">
                        {(selectedVersionDetail.findings || []).length} findings
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Rule-Set Version</span>
                      <span className="text-[11px] font-mono text-slate-600 mt-0.5 block truncate">
                        {selectedVersionDetail.ruleSetVersion || (selectedVersionDetail as any).rule_set_version || 'Standard Brand Rules'}
                      </span>
                    </div>
                  </div>

                  {/* Content & Findings Scrollable Body */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {/* Content Snapshot */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                        <span>Content Snapshot</span>
                        <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                          SHA-256: {(selectedVersionDetail.contentHash || (selectedVersionDetail as any).content_hash || '').slice(0, 12)}...
                          <button
                            onClick={() => handleCopy(selectedVersionDetail.contentHash || (selectedVersionDetail as any).content_hash || '', 'hash')}
                            className="hover:text-slate-700"
                            title="Copy SHA-256 hash"
                          >
                            {copiedHash ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </span>
                      </div>
                      <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-800 leading-relaxed font-sans whitespace-pre-wrap select-text">
                        {selectedVersionDetail.content}
                      </div>
                    </div>

                    {/* Associated Findings for this Version */}
                    <div className="space-y-2 pt-2 border-t border-slate-100">
                      <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                        <span className="flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                          <span>Version Findings ({(selectedVersionDetail.findings || []).length})</span>
                        </span>
                        <span className="text-[11px] text-slate-400 font-normal">
                          Scoped specifically to v{selectedVersionDetail.versionNumber ?? (selectedVersionDetail as any).version_number ?? 1}
                        </span>
                      </div>

                      {(selectedVersionDetail.findings || []).length === 0 ? (
                        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                          <span>No compliance violations detected in this version snapshot.</span>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {(selectedVersionDetail.findings || []).map((f, idx) => (
                            <div
                              key={f.id || idx}
                              className="p-3 rounded-lg border border-slate-200 bg-slate-50/60 space-y-1.5 text-xs"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-1.5">
                                  <Badge
                                    variant={
                                      f.severity === 'critical'
                                        ? 'destructive'
                                        : f.severity === 'moderate'
                                        ? 'warning'
                                        : 'outline'
                                    }
                                    className="text-[10px] uppercase font-bold"
                                  >
                                    {f.severity}
                                  </Badge>
                                  <span className="font-semibold text-slate-800">
                                    {f.category}
                                  </span>
                                </div>
                                <span className="text-[10px] text-slate-400 font-mono">
                                  Finding #{f.id}
                                </span>
                              </div>

                              <div className="text-slate-600 text-[11px]">
                                <span className="font-semibold text-slate-700">Excerpt: </span>
                                <span className="bg-rose-50 text-rose-800 px-1 py-0.5 rounded border border-rose-200 font-mono">
                                  "{f.originalText}"
                                </span>
                              </div>

                              <div className="text-slate-600 text-[11px] leading-relaxed">
                                {f.explanation}
                              </div>

                              {f.suggestedCorrection && (
                                <div className="text-[11px] bg-emerald-50 text-emerald-900 p-2 rounded border border-emerald-200 mt-1">
                                  <span className="font-semibold">Suggested Correction: </span>
                                  <span>"{f.suggestedCorrection}"</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center p-8 text-slate-400 text-xs">
                  Select a version on the left to inspect its complete content and findings.
                </div>
              )}
            </div>
          </div>

          {/* Modal Footer */}
          <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-slate-500 shrink-0">
            <span className="flex items-center gap-1.5 text-slate-500">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              All version records are cryptographically verified and immutable.
            </span>
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>

      {/* Interactive Version Diff Modal */}
      {isCompareDiffOpen && (
        <CompareDiffModal
          reviewId={reviewId ? Number(reviewId) : undefined}
          isOpen={isCompareDiffOpen}
          onClose={() => setIsCompareDiffOpen(false)}
          scoreBefore={
            versionsList.find((v) => v.versionNumber === compareSourceNum)?.complianceScore ?? 100
          }
          scoreAfter={
            versionsList.find((v) => v.versionNumber === compareTargetNum)?.complianceScore ?? 100
          }
          initialSourceVersion={compareSourceNum}
          initialTargetVersion={compareTargetNum}
          versions={versionsList}
          currentVersionNumber={currentVersionNumber}
        />
      )}
    </div>
  )
}
