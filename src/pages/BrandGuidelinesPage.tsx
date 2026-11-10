import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { OverviewTab } from '@/components/guidelines/OverviewTab'
import { ApprovedGuidelinesTab } from '@/components/guidelines/ApprovedGuidelinesTab'
import { PendingExtractionTab } from '@/components/guidelines/PendingExtractionTab'
import { SourceDocumentsTab } from '@/components/guidelines/SourceDocumentsTab'
import { RuleEditModal } from '@/components/guidelines/RuleEditModal'
import { useGovernance } from '@/context/GovernanceContext'
import { useAuth } from '@/context/AuthContext'
import type {
  ApprovedRule,
  PendingCandidateRule,
  SourceDocument,
} from '@/types/guidelines'
import {
  BookOpen,
  CheckCircle2,
  Clock,
  FileText,
  Plus,
  UploadCloud,
} from 'lucide-react'

type TabType = 'overview' | 'approved' | 'pending' | 'documents'

export const BrandGuidelinesPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const { user } = useAuth()

  const {
    approvedRules,
    pendingCandidates,
    sourceDocuments,
    addApprovedRule,
    updateApprovedRule,
    deleteApprovedRule,
    approveCandidateRule,
    rejectCandidateRule,
    approveAllHighConfidenceCandidates,
    uploadSourceDocument,
    uploadDocumentFile,
    deleteSourceDocument,
  } = useGovernance()

  // Rule Edit Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<ApprovedRule | null>(null)
  const [editingCandidateId, setEditingCandidateId] = useState<string | null>(null)

  // Edit Candidate Rule before approving
  const handleEditCandidate = (candidate: PendingCandidateRule) => {
    setEditingCandidateId(candidate.id)
    setEditingRule({
      id: candidate.id,
      code: 'NEW',
      category: candidate.category,
      subCategory: candidate.subCategory,
      title: candidate.title,
      description: candidate.extractedText,
      enforcementLevel: candidate.suggestedEnforcement,
      sourceDocument: candidate.sourceDocument,
      sourcePage: candidate.sourceSection,
      lastUpdated: 'Draft',
      updatedBy: user?.name || 'Workspace Admin',
    })
    setIsEditModalOpen(true)
  }

  // Save Rule (handles both new/edited approved rules and edited pending candidates)
  const handleSaveRule = (rule: ApprovedRule) => {
    if (editingCandidateId) {
      addApprovedRule(rule)
      rejectCandidateRule(editingCandidateId) // removes from pending
      setEditingCandidateId(null)
    } else if (editingRule) {
      updateApprovedRule(rule)
    } else {
      addApprovedRule(rule)
    }
    setEditingRule(null)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      {/* Page Header */}
      <PageHeader
        title="Brand Knowledge Management"
        description="Hybrid governance engine: AI extracts candidate guidelines from source files, requiring authorized human approval before becoming official brand law."
        badge={
          <Badge variant="blue" className="gap-1 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            Knowledge Base v2.4
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={() => setActiveTab('documents')}
            >
              <UploadCloud className="w-3.5 h-3.5 text-slate-600" />
              <span>Upload Guidelines</span>
            </Button>

            <Button
              variant="primaryBlue"
              size="sm"
              className="gap-1.5 text-xs font-semibold shadow-xs"
              onClick={() => {
                setEditingRule(null)
                setEditingCandidateId(null)
                setIsEditModalOpen(true)
              }}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Guideline Rule</span>
            </Button>
          </div>
        }
      />

      {/* Four Main Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-border">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'overview'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('approved')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'approved'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
          }`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Approved Guidelines</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700">
            {approvedRules.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('pending')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all relative ${
            activeTab === 'pending'
              ? 'border-amber-600 text-amber-700'
              : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
          }`}
        >
          <Clock className="w-3.5 h-3.5 text-amber-600" />
          <span>Pending AI Extraction</span>
          {pendingCandidates.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-800 font-bold">
              {pendingCandidates.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('documents')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'documents'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Source Documents</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700">
            {sourceDocuments.length}
          </span>
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <OverviewTab
          totalApprovedRules={approvedRules.length}
          pendingApprovalsCount={pendingCandidates.length}
          uploadedDocumentsCount={sourceDocuments.length}
          lastUpdated="Today, 2:15 PM"
          onSwitchTab={(t) => setActiveTab(t)}
          onAddRuleClick={() => {
            setEditingRule(null)
            setEditingCandidateId(null)
            setIsEditModalOpen(true)
          }}
        />
      )}

      {/* Tab 2: Approved Guidelines */}
      {activeTab === 'approved' && (
        <ApprovedGuidelinesTab
          rules={approvedRules}
          onAddRule={() => {
            setEditingRule(null)
            setEditingCandidateId(null)
            setIsEditModalOpen(true)
          }}
          onEditRule={(rule) => {
            setEditingRule(rule)
            setEditingCandidateId(null)
            setIsEditModalOpen(true)
          }}
          onDeleteRule={deleteApprovedRule}
        />
      )}

      {/* Tab 3: Pending AI Extraction */}
      {activeTab === 'pending' && (
        <PendingExtractionTab
          candidates={pendingCandidates}
          onApproveCandidate={approveCandidateRule}
          onRejectCandidate={rejectCandidateRule}
          onEditCandidate={handleEditCandidate}
          onApproveAllHighConfidence={approveAllHighConfidenceCandidates}
        />
      )}

      {/* Tab 4: Source Documents */}
      {activeTab === 'documents' && (
        <SourceDocumentsTab
          documents={sourceDocuments}
          onUploadDocument={uploadSourceDocument}
          onUploadFile={uploadDocumentFile}
          onDeleteDocument={deleteSourceDocument}
          onReExtract={() => {}}
          onGoToPendingQueue={() => setActiveTab('pending')}
        />
      )}

      {/* Add / Edit Rule Modal */}
      <RuleEditModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false)
          setEditingRule(null)
          setEditingCandidateId(null)
        }}
        onSaveRule={handleSaveRule}
        initialRule={editingRule}
      />
    </motion.div>
  )
}
