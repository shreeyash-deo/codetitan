import React, { useState, useEffect } from 'react'
import type { ApprovedRule, GuidelineCategory, EnforcementLevel } from '@/types/guidelines'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { X, BookOpen, Save, Plus } from 'lucide-react'

interface RuleEditModalProps {
  isOpen: boolean
  onClose: () => void
  onSaveRule: (rule: ApprovedRule) => void
  initialRule?: ApprovedRule | null
  defaultCategory?: GuidelineCategory
}

export const RuleEditModal: React.FC<RuleEditModalProps> = ({
  isOpen,
  onClose,
  onSaveRule,
  initialRule,
  defaultCategory = 'Brand Voice',
}) => {
  if (!isOpen) return null

  const isEditing = Boolean(initialRule)

  const [title, setTitle] = useState(initialRule?.title || '')
  const [category, setCategory] = useState<GuidelineCategory>(
    initialRule?.category || defaultCategory
  )
  const [subCategory, setSubCategory] = useState(initialRule?.subCategory || '')
  const [description, setDescription] = useState(initialRule?.description || '')
  const [enforcementLevel, setEnforcementLevel] = useState<EnforcementLevel>(
    initialRule?.enforcementLevel || 'Strict'
  )
  const [approvedExample, setApprovedExample] = useState(
    initialRule?.examples?.approved || ''
  )
  const [prohibitedExample, setProhibitedExample] = useState(
    initialRule?.examples?.prohibited || ''
  )
  const [sourceDocument, setSourceDocument] = useState(
    initialRule?.sourceDocument || 'NovaPay_Global_Brand_Guidelines_v2.4.pdf'
  )
  const [sourcePage, setSourcePage] = useState(initialRule?.sourcePage || '')

  useEffect(() => {
    if (initialRule) {
      setTitle(initialRule.title)
      setCategory(initialRule.category)
      setSubCategory(initialRule.subCategory)
      setDescription(initialRule.description)
      setEnforcementLevel(initialRule.enforcementLevel)
      setApprovedExample(initialRule.examples?.approved || '')
      setProhibitedExample(initialRule.examples?.prohibited || '')
      setSourceDocument(initialRule.sourceDocument || '')
      setSourcePage(initialRule.sourcePage || '')
    } else {
      setTitle('')
      setCategory(defaultCategory)
      setSubCategory('General Rule')
      setDescription('')
      setEnforcementLevel('Strict')
      setApprovedExample('')
      setProhibitedExample('')
      setSourceDocument('NovaPay_Global_Brand_Guidelines_v2.4.pdf')
      setSourcePage('')
    }
  }, [initialRule, defaultCategory])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !description.trim()) return

    const prefixMap: Record<GuidelineCategory, string> = {
      'Brand Voice': 'BV',
      'Terminology': 'TM',
      'Brand Facts': 'BF',
      'Claims & Restrictions': 'CR',
      'Visual Identity': 'VI',
    }

    const savedRule: ApprovedRule = {
      id: initialRule?.id || `rule-${Date.now()}`,
      code: initialRule?.code || `${prefixMap[category]}-${Math.floor(10 + Math.random() * 90)}`,
      category,
      subCategory: subCategory || 'General Rule',
      title: title.trim(),
      description: description.trim(),
      enforcementLevel,
      examples:
        approvedExample || prohibitedExample
          ? {
              approved: approvedExample.trim(),
              prohibited: prohibitedExample.trim(),
            }
          : undefined,
      sourceDocument: sourceDocument.trim() || undefined,
      sourcePage: sourcePage.trim() || undefined,
      lastUpdated: 'Just now',
      updatedBy: 'Sarah Chen (Brand Lead)',
    }

    onSaveRule(savedRule)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-xl rounded-xl bg-white shadow-2xl border border-border p-6 space-y-4 animate-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <BookOpen className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  {isEditing ? 'Edit Brand Rule' : 'Create Approved Guideline Rule'}
                </h3>
                <p className="text-xs text-slate-500">
                  Official authoritative brand governance rule
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

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            {/* Title & Category */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Rule Title</label>
                <Input
                  required
                  placeholder="e.g. Canonical Naming: 'NovaPay Subscriptions'"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as GuidelineCategory)}
                  className="w-full h-8 rounded-md border border-input bg-white px-2.5 py-1 text-xs text-slate-800 shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="Brand Voice">Brand Voice</option>
                  <option value="Terminology">Terminology</option>
                  <option value="Brand Facts">Brand Facts</option>
                  <option value="Claims & Restrictions">Claims & Restrictions</option>
                  <option value="Visual Identity">Visual Identity</option>
                </select>
              </div>
            </div>

            {/* Sub-category & Enforcement Level */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Sub-Category / Scope</label>
                <Input
                  placeholder="e.g. Product naming conventions"
                  value={subCategory}
                  onChange={(e) => setSubCategory(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Enforcement Strictness</label>
                <select
                  value={enforcementLevel}
                  onChange={(e) => setEnforcementLevel(e.target.value as EnforcementLevel)}
                  className="w-full h-8 rounded-md border border-input bg-white px-2.5 py-1 text-xs text-slate-800 shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="Strict">Strict (Block publish on violation)</option>
                  <option value="Advisory">Advisory (Show warning to creators)</option>
                </select>
              </div>
            </div>

            {/* Rule Description */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Rule Description & Rationale</label>
              <textarea
                required
                rows={3}
                placeholder="Describe the governance boundary, rationale, and specific requirements..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-md border border-input bg-white p-2.5 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            {/* Examples: Approved vs Prohibited */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-emerald-800">Approved Example (Do)</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Automate billing with NovaPay Subscriptions."
                  value={approvedExample}
                  onChange={(e) => setApprovedExample(e.target.value)}
                  className="w-full rounded-md border border-emerald-300 bg-emerald-50/30 p-2 text-xs shadow-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-rose-800">Prohibited Example (Don't)</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Deploy NovaPay Billing Suite."
                  value={prohibitedExample}
                  onChange={(e) => setProhibitedExample(e.target.value)}
                  className="w-full rounded-md border border-rose-300 bg-rose-50/30 p-2 text-xs shadow-xs"
                />
              </div>
            </div>

            {/* Source Reference */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 border-t border-border">
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Source Document</label>
                <Input
                  placeholder="e.g. NovaPay_Global_Brand_Guidelines_v2.4.pdf"
                  value={sourceDocument}
                  onChange={(e) => setSourceDocument(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Section / Page Citation</label>
                <Input
                  placeholder="e.g. Page 14, Section 2.3"
                  value={sourcePage}
                  onChange={(e) => setSourcePage(e.target.value)}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
              <Button type="button" variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" variant="primaryBlue" size="sm" className="gap-1.5 font-semibold">
                <Save className="w-3.5 h-3.5" />
                <span>{isEditing ? 'Save Changes' : 'Create Approved Rule'}</span>
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
