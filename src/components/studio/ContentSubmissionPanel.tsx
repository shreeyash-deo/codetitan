import React, { useState, useRef } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import type { StudioContentType } from '@/types/reviewStudio'
import { studioPresets } from '@/data/mockStudioPresets'
import {
  FileText,
  UploadCloud,
  Sparkles,
  Shield,
  Layers,
  FileCheck,
  FileCode,
  Image as ImageIcon,
  CheckCircle2,
  Trash2,
  RotateCcw,
  Copy,
} from 'lucide-react'

interface ContentSubmissionPanelProps {
  title: string
  setTitle: (val: string) => void
  contentType: StudioContentType
  setContentType: (val: StudioContentType) => void
  content: string
  setContent: (val: string) => void
  workspaceName: string
  onRunReview: () => void
  isAnalyzing: boolean
  onSelectPreset: (presetId: string) => void
  selectedFile: File | null
  setSelectedFile: (file: File | null) => void
}

export const ContentSubmissionPanel: React.FC<ContentSubmissionPanelProps> = ({
  title,
  setTitle,
  contentType,
  setContentType,
  content,
  setContent,
  workspaceName,
  onRunReview,
  isAnalyzing,
  onSelectPreset,
  selectedFile,
  setSelectedFile,
}) => {
  const [activeTab, setActiveTab] = useState<'text' | 'file'>('text')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Document statistics
  const charCount = content.length
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0
  const estimatedReadTime = Math.ceil(wordCount / 200)

  const contentTypes: StudioContentType[] = [
    'Social media',
    'Advertisement',
    'Blog',
    'Email',
    'Website copy',
    'Other',
  ]

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0]
      setSelectedFile(file)
      if (!title) setTitle(file.name.replace(/\.[^/.]+$/, ''))
      // If text/doc, mock reading it into the editor
      setContent(`[Extracted from document: ${file.name}]\n\nBoost your e-commerce checkout conversions by 40% with NovaPay.\n\nThe world's fastest payment API is here, crushing legacy slow banks with sub-second clearing. NovaPay Billing Suite provides 100% zero fraud guaranteed for high-volume enterprise stores.`)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]
      setSelectedFile(file)
      if (!title) setTitle(file.name.replace(/\.[^/.]+$/, ''))
      setContent(`[Extracted from document: ${file.name}]\n\nBoost your e-commerce checkout conversions by 40% with NovaPay.\n\nThe world's fastest payment API is here, crushing legacy slow banks with sub-second clearing. NovaPay Billing Suite provides 100% zero fraud guaranteed for high-volume enterprise stores.`)
    }
  }

  return (
    <Card className="h-full border-border/80 shadow-xs flex flex-col justify-between">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base font-semibold text-slate-900">
                Content Submission
              </CardTitle>
              <Badge variant="blue" className="text-[10px] gap-1 font-mono">
                <Shield className="w-3 h-3 text-blue-600" />
                {workspaceName}
              </Badge>
            </div>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Input copy, upload campaign collateral, or load compliance benchmark presets
            </CardDescription>
          </div>

          {/* Quick Presets Dropdown */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            <span className="text-[10px] font-semibold uppercase text-slate-400 shrink-0">
              Presets:
            </span>
            {studioPresets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => onSelectPreset(preset.id)}
                className="text-[11px] px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors whitespace-nowrap"
              >
                {preset.title.split(':')[0]}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-4 flex-1 flex flex-col">
        {/* Content Name & Type Row */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          <div className="sm:col-span-7 space-y-1">
            <label className="text-xs font-semibold text-slate-700">
              Asset / Campaign Title
            </label>
            <Input
              placeholder="e.g. Q4 Global Checkout Paid Ad Campaign"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="text-xs"
            />
          </div>

          <div className="sm:col-span-5 space-y-1">
            <label className="text-xs font-semibold text-slate-700">
              Content Type
            </label>
            <select
              value={contentType}
              onChange={(e) => setContentType(e.target.value as StudioContentType)}
              className="w-full h-8 rounded-md border border-input bg-white px-2.5 py-1 text-xs text-slate-800 shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {contentTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Input Mode Tabs: Text Editor vs Drag-and-Drop Upload */}
        <div className="flex items-center justify-between border-b border-border/80 pb-2">
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-md text-xs font-medium">
            <button
              type="button"
              onClick={() => setActiveTab('text')}
              className={`px-3 py-1 rounded transition-all flex items-center gap-1.5 ${
                activeTab === 'text'
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Text Editor</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('file')}
              className={`px-3 py-1 rounded transition-all flex items-center gap-1.5 ${
                activeTab === 'file'
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>File Upload {selectedFile && '✓'}</span>
            </button>
          </div>

          {/* Quick stats pill */}
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
            <span>{charCount} chars</span>
            <span>•</span>
            <span>{wordCount} words</span>
            <span>•</span>
            <span>{estimatedReadTime}m read</span>
          </div>
        </div>

        {/* Tab 1: Text Editor */}
        {activeTab === 'text' && (
          <div className="flex-1 flex flex-col space-y-1 min-h-[260px]">
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste or write marketing draft copy, campaign slogans, or landing page copy here..."
              className="flex-1 w-full rounded-md border border-input bg-white p-3.5 text-xs text-slate-800 leading-relaxed shadow-inner focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring placeholder:text-slate-400 resize-none font-sans"
            />
          </div>
        )}

        {/* Tab 2: Drag & Drop File Upload */}
        {activeTab === 'file' && (
          <div className="flex-1 flex flex-col justify-center min-h-[260px]">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.svg"
              className="hidden"
            />

            {!selectedFile ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsDragging(true)
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors flex flex-col items-center justify-center h-full ${
                  isDragging
                    ? 'border-blue-500 bg-blue-50/50'
                    : 'border-slate-200 hover:border-blue-400 bg-slate-50/40'
                }`}
              >
                <UploadCloud className="w-9 h-9 text-blue-600 mb-2.5 animate-bounce" />
                <h4 className="text-xs font-semibold text-slate-800">
                  Drag and drop your marketing document here
                </h4>
                <p className="text-[11px] text-slate-400 mt-1 max-w-sm">
                  Or click to browse from your computer. Our optical analyzer extracts copy and validates imagery.
                </p>

                {/* Supported File Type Indicators */}
                <div className="mt-4 flex items-center gap-2 flex-wrap justify-center">
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    <FileText className="w-3 h-3 text-red-500" /> PDF
                  </span>
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    <FileCode className="w-3 h-3 text-blue-500" /> DOCX
                  </span>
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    <ImageIcon className="w-3 h-3 text-emerald-500" /> PNG / JPG
                  </span>
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    <Layers className="w-3 h-3 text-purple-500" /> Max 50MB
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-blue-50/60 border border-blue-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-md bg-white border border-blue-200 flex items-center justify-center text-blue-600 shadow-2xs">
                    <FileCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-900">
                      {selectedFile.name}
                    </h4>
                    <p className="text-[11px] text-slate-500">
                      {(selectedFile.size / 1024).toFixed(1)} KB • Document text extracted into editor
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-xs h-7"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Change
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-slate-400 hover:text-rose-600"
                    onClick={() => {
                      setSelectedFile(null)
                      setContent('')
                    }}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Primary Action Button Bar */}
        <div className="pt-3 border-t border-border flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              setContent('')
              setTitle('')
              setSelectedFile(null)
            }}
            className="text-xs text-slate-400 hover:text-slate-700 inline-flex items-center gap-1 transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset Form</span>
          </button>

          <Button
            type="button"
            variant="primaryBlue"
            size="default"
            disabled={isAnalyzing || !content.trim()}
            onClick={onRunReview}
            className="gap-2 font-semibold shadow-sm px-5"
          >
            <Sparkles className="w-4 h-4" />
            <span>Run Brand Review</span>
            <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[9px] font-mono text-white/80 bg-black/20 rounded">
              ⌘↵
            </kbd>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
