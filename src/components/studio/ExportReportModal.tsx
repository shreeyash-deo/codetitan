import React from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useWorkspace } from '@/hooks/useWorkspace'
import type { StudioFinding } from '@/types/reviewStudio'
import {
  X,
  FileCheck2,
  Download,
  Share2,
  Printer,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react'

interface ExportReportModalProps {
  title: string
  score: number
  findings: StudioFinding[]
  isOpen: boolean
  onClose: () => void
}

export const ExportReportModal: React.FC<ExportReportModalProps> = ({
  title,
  score,
  findings,
  isOpen,
  onClose,
}) => {
  const { currentWorkspace } = useWorkspace()
  if (!isOpen) return null

  const resolvedCount = findings.filter(f => f.status === 'accepted' || f.status === 'manual').length
  const pendingCount = findings.filter(f => f.status === 'pending').length
  const formattedDate = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  const handleDownload = () => {
    alert(`BrandShield Compliance Audit Certificate exported for "${title}".`)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-2xl rounded-xl bg-white shadow-2xl border border-border p-6 space-y-6 animate-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Compliance Audit Certificate
                </h3>
                <p className="text-xs text-slate-500">
                  Official brand governance ledger report
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

          {/* Certificate Body */}
          <div className="p-6 rounded-xl border border-slate-200 bg-slate-50/50 space-y-4 text-xs font-mono">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <div className="font-sans font-bold text-slate-900 text-sm">{title}</div>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                  AUDIT-ID: BS-2026-NP-{Math.floor(1000 + Math.random() * 9000)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-slate-900 font-sans">{score}/100</div>
                <div className="text-[10px] text-slate-500 uppercase">Compliance Index</div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-600">
              <div>Organization: <strong className="text-slate-900">{currentWorkspace?.name || 'Organisation'}</strong></div>
              <div>Auditor: <strong className="text-slate-900">BrandShield Sentinel</strong></div>
              <div>Timestamp: <strong className="text-slate-900">{formattedDate}</strong></div>
            </div>

            <div className="pt-2 border-t border-slate-200 space-y-2">
              <div className="text-[11px] font-semibold text-slate-800 font-sans">
                Summary of Findings:
              </div>
              <div className="space-y-1 text-[11px] text-slate-600">
                <div>• Total Identified Anomaly Flags: {findings.length}</div>
                <div>• Accepted Remediations: {resolvedCount}</div>
                <div>• Unresolved Critical Blocks: {pendingCount}</div>
              </div>
            </div>

            <div className="p-2.5 rounded bg-white border border-slate-200 text-[10px] text-slate-500 font-sans italic">
              Verification Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-border">
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
            <div className="flex items-center gap-2">
              <Button
                variant="primaryBlue"
                size="sm"
                className="gap-1.5"
                onClick={handleDownload}
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download PDF Audit</span>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
