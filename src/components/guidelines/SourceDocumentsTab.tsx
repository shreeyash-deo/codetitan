import React, { useState, useRef } from 'react'
import type { SourceDocument } from '@/types/guidelines'
import { apiClient } from '@/services'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  UploadCloud,
  FileText,
  FileCode,
  Sparkles,
  Loader2,
  CheckCircle2,
  Trash2,
  RefreshCw,
  ExternalLink,
  Layers,
  ArrowRight,
  AlertCircle,
  AlertTriangle,
} from 'lucide-react'

interface SourceDocumentsTabProps {
  documents: SourceDocument[]
  onUploadDocument: (newDoc: SourceDocument) => void
  onUploadFile?: (file: File) => Promise<void>
  onDeleteDocument: (docId: string) => void
  onReExtract: (docId: string) => void
  onGoToPendingQueue: () => void
  isAdmin?: boolean
}

export const SourceDocumentsTab: React.FC<SourceDocumentsTabProps> = ({
  documents,
  onUploadDocument,
  onUploadFile,
  onDeleteDocument,
  onReExtract,
  onGoToPendingQueue,
  isAdmin = true,
}) => {
  const [isDragging, setIsDragging] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)
  const [reExtractingDocId, setReExtractingDocId] = useState<string | null>(null)
  const [extractionProgress, setExtractionProgress] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleReExtract = async (docId: string) => {
    setReExtractingDocId(docId)
    try {
      await onReExtract(docId)
    } finally {
      setReExtractingDocId(null)
    }
  }

  const handleProcessFile = (file: File) => {
    if (onUploadFile && !apiClient.isMockMode()) {
      setIsExtracting(true)
      setExtractionProgress(`Uploading and parsing ${file.name} with AI...`)
      onUploadFile(file).finally(() => setIsExtracting(false))
    } else {
      handleSimulateExtraction(file.name, file.size)
    }
  }

  const handleSimulateExtraction = (fileName: string, fileSize: number) => {
    setIsExtracting(true)
    setExtractionProgress('Ingesting and parsing document structure...')

    setTimeout(() => {
      setExtractionProgress('Performing OCR & text chunking across pages...')
    }, 700)

    setTimeout(() => {
      setExtractionProgress('Vectorizing embeddings & identifying brand guidelines...')
    }, 1400)

    setTimeout(() => {
      setIsExtracting(false)
      const newDoc: SourceDocument = {
        id: `doc-${Date.now()}`,
        name: fileName,
        format: fileName.toLowerCase().endsWith('.docx') ? 'DOCX' : 'PDF',
        size: `${(fileSize / (1024 * 1024)).toFixed(1)} MB`,
        pages: Math.floor(12 + Math.random() * 24),
        uploadedAt: 'Today',
        uploadedBy: 'Sarah Chen (Brand Lead)',
        status: 'extracted',
        extractedCandidatesCount: Math.floor(3 + Math.random() * 5),
        approvedRulesCount: 0,
      }
      onUploadDocument(newDoc)
    }, 2100)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleProcessFile(e.target.files[0])
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleProcessFile(e.dataTransfer.files[0])
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload Area for PDF & DOCX (Admin only) */}
      {isAdmin ? (
        <Card className="border-border">
          <CardContent className="p-6">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.docx,.txt"
              className="hidden"
            />

            {!isExtracting ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsDragging(true)
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-blue-500 bg-blue-50/60'
                    : 'border-slate-200 hover:border-blue-400 bg-slate-50/50'
                }`}
              >
                <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 border border-blue-200 flex items-center justify-center mx-auto mb-3 shadow-2xs">
                  <UploadCloud className="w-6 h-6 animate-pulse" />
                </div>

                <h3 className="text-sm font-bold text-slate-900">
                  Upload New Brand Guideline Manuals or Policy Memos
                </h3>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto leading-relaxed">
                  Drag and drop your official Brand Guidelines (.PDF or .DOCX). BrandShield AI will parse the document, extract candidate rules, and queue them for your review.
                </p>

                <div className="mt-4 flex items-center justify-center gap-2">
                  <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    <FileText className="w-3.5 h-3.5 text-red-500" /> PDF Guidelines
                  </span>
                  <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    <FileCode className="w-3.5 h-3.5 text-blue-500" /> DOCX Manuals
                  </span>
                  <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    <Layers className="w-3.5 h-3.5 text-purple-500" /> Max 100MB
                  </span>
                </div>
              </div>
            ) : (
              /* Animated Extraction Process State */
              <div className="p-8 text-center space-y-4 bg-blue-50/40 rounded-xl border border-blue-200">
                <div className="w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center mx-auto shadow-md">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>

                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-slate-900">
                    AI Knowledge Extraction in Progress
                  </h4>
                  <p className="text-xs text-blue-700 font-mono animate-pulse">
                    {extractionProgress}
                  </p>
                </div>

                <div className="w-full max-w-md mx-auto h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-600 rounded-full animate-pulse w-3/4" />
                </div>

                <p className="text-[11px] text-slate-400 italic">
                  Extraction parses tone, claims, color tokens, and product terminology into candidate rules.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-xl border border-blue-200/70 bg-blue-50/40 p-4 text-xs text-blue-900 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
            <FileText className="w-4 h-4 text-blue-700" />
          </div>
          <div>
            <p className="font-semibold text-slate-900">Brand Guideline Repository (Read-Only)</p>
            <p className="text-slate-600 mt-0.5">
              Viewing official source documents for this organisation. Uploading documents and triggering rule extraction requires Administrator permissions.
            </p>
          </div>
        </div>
      )}

      {/* Uploaded Documents Repository Table */}
      <Card>
        <CardHeader className="pb-3 border-b border-border/70">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base font-semibold text-slate-900">
                Source Document Repository
              </CardTitle>
              <CardDescription className="text-xs text-slate-500 mt-0.5">
                Authoritative brand files indexed into vector memory
              </CardDescription>
            </div>

            {isAdmin && (
              <Button
                variant="outline"
                size="sm"
                onClick={onGoToPendingQueue}
                className="text-xs gap-1"
              >
                <span>View Review Queue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="px-5 py-3">Document Title</th>
                  <th className="px-4 py-3">Format & Size</th>
                  <th className="px-4 py-3">Pages</th>
                  <th className="px-4 py-3">Uploaded Date</th>
                  <th className="px-4 py-3">Extracted Candidates</th>
                  <th className="px-4 py-3">Approved Rules</th>
                  {isAdmin && <th className="px-4 py-3 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/60 transition-colors">
                    {/* Document title & uploader */}
                    <td className="px-5 py-3.5 font-medium text-slate-900 max-w-xs truncate">
                      <div className="flex items-center gap-2">
                        {doc.format === 'PDF' ? (
                          <FileText className="w-4 h-4 text-red-500 shrink-0" />
                        ) : (
                          <FileCode className="w-4 h-4 text-blue-500 shrink-0" />
                        )}
                        <span className="truncate">{doc.name}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 pl-6 block">
                        Uploaded by {doc.uploadedBy}
                      </span>
                    </td>

                    {/* Format & Size */}
                    <td className="px-4 py-3.5 whitespace-nowrap text-slate-600">
                      <Badge variant="outline" className="text-[10px] font-mono mr-1.5">
                        {doc.format}
                      </Badge>
                      {doc.size}
                    </td>

                    {/* Pages */}
                    <td className="px-4 py-3.5 whitespace-nowrap text-slate-600">
                      {doc.pages} pages
                    </td>

                    {/* Uploaded Date */}
                    <td className="px-4 py-3.5 whitespace-nowrap text-slate-600">
                      {doc.uploadedAt}
                    </td>

                    {/* Extracted Candidates */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      {doc.status === 'text_failed' ? (
                        <span
                          className="inline-flex items-center gap-1 font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[11px] border border-amber-200"
                          title="Text extraction failed from file"
                        >
                          <AlertTriangle className="w-3 h-3 text-amber-600" />
                          Text Failed
                        </span>
                      ) : doc.status === 'ai_failed' || doc.status === 'failed' ? (
                        <span
                          className="inline-flex items-center gap-1 font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded text-[11px] border border-rose-200"
                          title="Text preserved, AI rule extraction failed"
                        >
                          <AlertCircle className="w-3 h-3 text-rose-600" />
                          AI Failed
                        </span>
                      ) : doc.status === 'empty' ? (
                        <span className="inline-flex items-center gap-1 font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded text-[11px] border border-slate-200">
                          Empty Doc
                        </span>
                      ) : doc.status === 'duplicate' ? (
                        <span
                          className="inline-flex items-center gap-1 font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[11px] border border-amber-200"
                          title="All extracted rules already exist in workspace"
                        >
                          All Duplicates
                        </span>
                      ) : doc.status === 'no_candidates' ? (
                        <span className="inline-flex items-center gap-1 font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded text-[11px] border border-slate-200">
                          0 Found
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded text-[11px] border border-blue-200">
                          <Sparkles className="w-3 h-3 text-blue-600" />
                          {doc.extractedCandidatesCount} candidates
                        </span>
                      )}
                    </td>

                    {/* Approved Rules */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-[11px] border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        {doc.approvedRulesCount} approved
                      </span>
                    </td>

                    {/* Actions (Admin only) */}
                    {isAdmin && (
                      <td className="px-4 py-3.5 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            title="Re-extract candidate rules"
                            disabled={reExtractingDocId === doc.id}
                            onClick={() => handleReExtract(doc.id)}
                          >
                            {reExtractingDocId === doc.id ? (
                              <Loader2 className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                            ) : (
                              <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            title="Delete source file"
                            onClick={() => {
                              if (confirm(`Delete source document "${doc.name}"?`)) {
                                onDeleteDocument(doc.id)
                              }
                            }}
                          >
                            <Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-rose-600" />
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
