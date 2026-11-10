import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  mockBrandVoiceSummary,
  mockBrandIdentitySummary,
} from '@/data/mockKnowledgeBase'
import {
  BookOpen,
  Clock,
  FileText,
  Calendar,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
} from 'lucide-react'

interface OverviewTabProps {
  totalApprovedRules: number
  pendingApprovalsCount: number
  uploadedDocumentsCount: number
  lastUpdated: string
  onSwitchTab: (tabId: 'approved' | 'pending' | 'documents') => void
  onAddRuleClick: () => void
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  totalApprovedRules,
  pendingApprovalsCount,
  uploadedDocumentsCount,
  lastUpdated,
  onSwitchTab,
  onAddRuleClick,
}) => {
  const [copiedHex, setCopiedHex] = React.useState<string | null>(null)

  const copyToClipboard = (hex: string) => {
    navigator.clipboard.writeText(hex)
    setCopiedHex(hex)
    setTimeout(() => setCopiedHex(null), 1800)
  }

  return (
    <div className="space-y-6">
      {/* 4 Overview Telemetry KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Approved Rules */}
        <Card
          onClick={() => onSwitchTab('approved')}
          className="cursor-pointer hover:border-slate-300 transition-all p-4 select-none group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Approved Rules
            </span>
            <div className="p-1 rounded bg-blue-50 text-blue-600">
              <BookOpen className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {totalApprovedRules}
          </div>
          <p className="text-[11px] text-slate-500 mt-1 flex items-center gap-1 group-hover:text-blue-600 transition-colors">
            <span>Official authoritative knowledge</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </p>
        </Card>

        {/* Pending AI Extractions */}
        <Card
          onClick={() => onSwitchTab('pending')}
          className="cursor-pointer hover:border-amber-300 transition-all p-4 select-none bg-amber-50/20 border-amber-200/80 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider">
              Pending Approvals
            </span>
            <div className="p-1 rounded bg-amber-100 text-amber-700">
              <Clock className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {pendingApprovalsCount}
          </div>
          <p className="text-[11px] text-amber-700 font-medium mt-1 flex items-center gap-1">
            <span>Awaiting authorized human sign-off</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </p>
        </Card>

        {/* Uploaded Documents */}
        <Card
          onClick={() => onSwitchTab('documents')}
          className="cursor-pointer hover:border-slate-300 transition-all p-4 select-none group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Source Documents
            </span>
            <div className="p-1 rounded bg-slate-100 text-slate-600">
              <FileText className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {uploadedDocumentsCount}
          </div>
          <p className="text-[11px] text-slate-500 mt-1 flex items-center gap-1 group-hover:text-blue-600 transition-colors">
            <span>PDF and DOCX repositories</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </p>
        </Card>

        {/* Last Knowledge Update */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Last Knowledge Update
            </span>
            <div className="p-1 rounded bg-emerald-50 text-emerald-600">
              <Calendar className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-base font-bold text-slate-900 mt-2 truncate">
            {lastUpdated}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Signed off by Sarah Chen (Brand Lead)
          </p>
        </Card>
      </div>

      {/* Brand Voice Summary Section */}
      <Card>
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="text-base font-semibold text-slate-900">
                  Brand Voice Summary
                </CardTitle>
                <Badge variant="blue" className="text-[10px]">
                  {mockBrandVoiceSummary.readingLevel}
                </Badge>
              </div>
              <CardDescription className="text-xs text-slate-500 mt-0.5">
                Primary communicative tone: {mockBrandVoiceSummary.primaryTone}
              </CardDescription>
            </div>

            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => onSwitchTab('approved')}
            >
              View Voice Rules
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-5 space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
            {mockBrandVoiceSummary.description}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            {mockBrandVoiceSummary.pillars.map((pillar) => (
              <div
                key={pillar.trait}
                className="p-3.5 rounded-lg border border-border bg-slate-50/60 space-y-2 text-xs"
              >
                <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>{pillar.trait}</span>
                </div>

                <div className="space-y-1.5 text-[11px]">
                  <div className="text-emerald-800 bg-emerald-50 p-2 rounded border border-emerald-200/70">
                    <strong className="text-emerald-900 font-semibold block mb-0.5">Do:</strong>
                    {pillar.positive}
                  </div>
                  <div className="text-rose-800 bg-rose-50 p-2 rounded border border-rose-200/70">
                    <strong className="text-rose-900 font-semibold block mb-0.5">Don't:</strong>
                    {pillar.negative}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Brand Identity Overview Section */}
      <Card>
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base font-semibold text-slate-900">
                Brand Identity Overview
              </CardTitle>
              <CardDescription className="text-xs text-slate-500 mt-0.5">
                Core marks, isolation boundaries, typography stacks, and accessible color tokens
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="text-xs"
                onClick={onAddRuleClick}
              >
                Add Rule
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5 space-y-6">
          {/* Logo & Typography Guidelines */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400">
                Logo Isolation
              </span>
              <div className="font-semibold text-slate-900">24px Exclusion Zone</div>
              <p className="text-[11px] text-slate-500">{mockBrandIdentitySummary.logoClearspace}</p>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400">
                Minimum Size
              </span>
              <div className="font-semibold text-slate-900">32px Height (Digital)</div>
              <p className="text-[11px] text-slate-500">{mockBrandIdentitySummary.minimumLogoWidth}</p>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400">
                Primary Typeface
              </span>
              <div className="font-semibold text-slate-900">Inter</div>
              <p className="text-[11px] text-slate-500">{mockBrandIdentitySummary.primaryTypeface}</p>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400">
                Monospace Typeface
              </span>
              <div className="font-semibold text-slate-900">JetBrains Mono</div>
              <p className="text-[11px] text-slate-500">{mockBrandIdentitySummary.monoTypeface}</p>
            </div>
          </div>

          {/* Color Palette Swatches */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-800">
                Approved Enterprise Color Palette
              </span>
              <span className="text-[11px] text-slate-400">
                Click any swatch to copy HEX
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {mockBrandIdentitySummary.colors.map((color) => {
                const isCopied = copiedHex === color.hex
                return (
                  <div
                    key={color.name}
                    onClick={() => copyToClipboard(color.hex)}
                    className="p-3 rounded-lg border border-border bg-white hover:border-slate-300 transition-all cursor-pointer space-y-2 group"
                  >
                    {/* Swatch color block */}
                    <div
                      className="h-14 rounded-md w-full shadow-inner border border-black/10 flex items-end justify-end p-1.5 transition-transform group-hover:scale-[1.02]"
                      style={{ backgroundColor: color.hex }}
                    >
                      <span className="text-[10px] font-mono px-1 py-0.5 rounded bg-black/40 text-white font-medium">
                        {isCopied ? 'Copied!' : color.hex}
                      </span>
                    </div>

                    <div className="text-xs">
                      <div className="font-semibold text-slate-900 truncate flex items-center justify-between">
                        <span>{color.name}</span>
                        {isCopied ? (
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                        )}
                      </div>
                      <p className="text-[10px] text-slate-400 mt-0.5 font-mono">
                        RGB: {color.rgb}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-1 leading-tight line-clamp-2">
                        {color.usage}
                      </p>
                      <div className="mt-2 pt-1 border-t border-slate-100 text-[10px] text-emerald-700 font-medium">
                        {color.wcagContrast}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
