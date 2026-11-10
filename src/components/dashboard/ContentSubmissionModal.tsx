import React, { useState } from 'react'
import {
  X,
  Sparkles,
  UploadCloud,
  Globe,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import type { ReviewItem } from '@/types/review'

interface ContentSubmissionModalProps {
  isOpen: boolean
  onClose: () => void
  onAddReview: (newReview: ReviewItem) => void
}

export const ContentSubmissionModal: React.FC<ContentSubmissionModalProps> = ({
  isOpen,
  onClose,
  onAddReview,
}) => {
  if (!isOpen) return null

  const [mode, setMode] = useState<'text' | 'upload' | 'url'>('text')
  const [title, setTitle] = useState('')
  const [channel, setChannel] = useState<ReviewItem['channel']>('Blog')
  const [content, setContent] = useState('')
  const [url, setUrl] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState('')
  const [scanResult, setScanResult] = useState<{
    score: number
    issues: number
    summary: string
  } | null>(null)

  const handleStartScan = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    setIsScanning(true)
    setScanResult(null)

    // Simulate realistic multi-step AI scan
    setScanProgress('Tokenizing text & matching vector guidelines...')
    setTimeout(() => {
      setScanProgress('Analyzing voice, tone & colloquialisms...')
    }, 600)

    setTimeout(() => {
      setScanProgress('Checking statutory disclaimers & regulatory claims...')
    }, 1200)

    setTimeout(() => {
      setIsScanning(false)
      const calculatedScore = Math.floor(Math.random() * 20) + 78 // 78-98
      const calculatedIssues = calculatedScore >= 90 ? 0 : 2
      const res = {
        score: calculatedScore,
        issues: calculatedIssues,
        summary: calculatedScore >= 90
          ? 'Complies with NovaPay core tone & statutory parameters. Zero high-risk flags.'
          : 'Detected 2 minor phrasing discrepancies with NovaPay fintech voice standards.',
      }
      setScanResult(res)

      // Add to review list
      const newReview: ReviewItem = {
        id: `rev-${Date.now().toString().slice(-4)}`,
        title: title.trim(),
        channel: channel,
        contentType: `${channel} Draft`,
        author: {
          name: 'Sarah Chen',
          role: 'Brand Lead',
          email: 'sarah.chen@novapay.io',
          avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
        },
        score: calculatedScore,
        status: calculatedScore >= 90 ? 'approved' : 'flagged',
        issuesDetected: calculatedIssues,
        submittedAt: 'Just now',
        date: 'Today',
        brandGuidelineId: 'bg-voice',
        summary: res.summary,
        contentPreview: content || url || 'Uploaded asset content preview...',
        issues: calculatedIssues > 0 ? [
          {
            id: `iss-${Date.now()}`,
            category: 'Tone inconsistencies',
            severity: 'moderate',
            snippet: 'fastest ever on the market',
            explanation: 'Avoid superlatives without third-party compliance benchmarks.',
            suggestion: 'Use "Industry-leading sub-second clearing rails"',
          }
        ] : [],
      }

      onAddReview(newReview)
    }, 1800)
  }

  const handleFinish = () => {
    onClose()
    setTitle('')
    setContent('')
    setUrl('')
    setScanResult(null)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-xl rounded-xl bg-white shadow-2xl border border-border p-6 animate-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Review New Content
                </h3>
                <p className="text-xs text-slate-500">
                  Instant AI compliance scan against NovaPay brand guidelines
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {!scanResult ? (
            <form onSubmit={handleStartScan} className="space-y-4 pt-4">
              {/* Submission Mode Selector */}
              <div className="grid grid-cols-3 gap-2 p-1 bg-slate-100 rounded-lg text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setMode('text')}
                  className={`py-1.5 px-3 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                    mode === 'text' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Paste Text</span>
                </button>
                <button
                  type="button"
                  onClick={() => setMode('upload')}
                  className={`py-1.5 px-3 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                    mode === 'upload' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>Upload File</span>
                </button>
                <button
                  type="button"
                  onClick={() => setMode('url')}
                  className={`py-1.5 px-3 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                    mode === 'url' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>Live URL</span>
                </button>
              </div>

              {/* Title & Channel */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Content Name / Title</label>
                  <Input
                    required
                    placeholder="e.g. Q4 Merchant Checkout Campaign"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Publishing Channel</label>
                  <select
                    value={channel}
                    onChange={(e) => setChannel(e.target.value as ReviewItem['channel'])}
                    className="w-full h-8 rounded-md border border-input bg-white px-3 py-1 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring text-slate-800"
                  >
                    <option value="Blog">Product Blog Post</option>
                    <option value="Ad Creative">Ad Creative & Banners</option>
                    <option value="Social">Social Media (LinkedIn/X)</option>
                    <option value="Product Landing">Product Landing Page</option>
                    <option value="Email Campaign">Email Newsletter</option>
                    <option value="Press Release">Press Release</option>
                  </select>
                </div>
              </div>

              {/* Input Area Based on Mode */}
              {mode === 'text' && (
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Content Body / Copy</label>
                  <textarea
                    rows={4}
                    required
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Paste draft copy, marketing messaging, or ad headlines here..."
                    className="w-full rounded-md border border-input bg-white p-3 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring placeholder:text-slate-400"
                  />
                </div>
              )}

              {mode === 'upload' && (
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center hover:border-blue-400 transition-colors bg-slate-50/50">
                  <UploadCloud className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                  <p className="text-xs font-medium text-slate-700">
                    Drop PDF, DOCX, PNG, or Figma files here
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Supports up to 25MB with automated visual OCR
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-3 text-xs"
                    onClick={() => setContent('Simulated document upload: Q4_NovaPay_Campaign.pdf')}
                  >
                    Browse Files
                  </Button>
                </div>
              )}

              {mode === 'url' && (
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Public Page URL</label>
                  <Input
                    type="url"
                    required
                    placeholder="https://novapay.io/checkout-demo"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                  <p className="text-[11px] text-slate-400">
                    Our crawler will parse text, headings, meta tags, and logo assets.
                  </p>
                </div>
              )}

              {/* Loading progress during scan */}
              {isScanning && (
                <div className="p-3.5 rounded-lg bg-blue-50 border border-blue-200 flex items-center gap-3">
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin shrink-0" />
                  <span className="text-xs font-medium text-blue-900 animate-pulse">
                    {scanProgress}
                  </span>
                </div>
              )}

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onClose}
                  disabled={isScanning}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primaryBlue"
                  size="sm"
                  disabled={isScanning || !title.trim()}
                  className="gap-1.5"
                >
                  {isScanning ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Scanning...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Scan Against Guidelines</span>
                    </>
                  )}
                </Button>
              </div>
            </form>
          ) : (
            /* Instant Scan Results */
            <div className="space-y-5 pt-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center space-y-2">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-50 border border-blue-200 text-blue-600 mb-1">
                  <CheckCircle2 className="w-6 h-6 text-blue-600" />
                </div>
                <h4 className="text-base font-bold text-slate-900">
                  Scan Completed
                </h4>
                <div className="text-3xl font-extrabold text-slate-900">
                  {scanResult.score}
                  <span className="text-sm font-semibold text-slate-400">/100</span>
                </div>
                <p className="text-xs text-slate-600 max-w-md mx-auto">
                  {scanResult.summary}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-100 text-xs text-slate-600 flex items-center justify-between">
                <span>Added to NovaPay Review Queue</span>
                <Badge variant={scanResult.score >= 90 ? 'success' : 'warning'}>
                  {scanResult.score >= 90 ? 'Approved' : 'Flagged for Review'}
                </Badge>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  variant="primaryBlue"
                  size="sm"
                  onClick={handleFinish}
                  className="gap-1"
                >
                  <span>Done</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
