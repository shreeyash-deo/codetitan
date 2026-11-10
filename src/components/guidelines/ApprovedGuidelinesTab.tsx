import React, { useState } from 'react'
import type { ApprovedRule, GuidelineCategory } from '@/types/guidelines'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  Edit2,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Layers,
  ArrowRight,
} from 'lucide-react'

interface ApprovedGuidelinesTabProps {
  rules: ApprovedRule[]
  onAddRule: () => void
  onEditRule: (rule: ApprovedRule) => void
  onDeleteRule: (ruleId: string) => void
  isAdmin?: boolean
}

const categoriesList: { id: 'all' | GuidelineCategory; label: string; countBadge?: number }[] = [
  { id: 'all', label: 'All Categories' },
  { id: 'Brand Voice', label: 'Brand Voice' },
  { id: 'Terminology', label: 'Terminology' },
  { id: 'Brand Facts', label: 'Brand Facts' },
  { id: 'Claims & Restrictions', label: 'Claims & Restrictions' },
  { id: 'Visual Identity', label: 'Visual Identity' },
]

export const ApprovedGuidelinesTab: React.FC<ApprovedGuidelinesTabProps> = ({
  rules,
  onAddRule,
  onEditRule,
  onDeleteRule,
  isAdmin = true,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<'all' | GuidelineCategory>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredRules = rules.filter((rule) => {
    const matchesCategory =
      selectedCategory === 'all' || rule.category === selectedCategory
    const matchesSearch =
      rule.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rule.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rule.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rule.subCategory.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  return (
    <div className="space-y-6">
      {/* Search, Category Filter Bar & Add Action */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-white p-3 rounded-lg border border-border shadow-xs">
        {/* Category Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 lg:pb-0">
          {categoriesList.map((cat) => {
            const count =
              cat.id === 'all'
                ? rules.length
                : rules.filter((r) => r.category === cat.id).length
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0 ${
                  selectedCategory === cat.id
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <span>{cat.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    selectedCategory === cat.id
                      ? 'bg-slate-700 text-white'
                      : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {count}
                </span>
              </button>
            )
          })}
        </div>

        {/* Search Input & Add Button */}
        <div className="flex items-center gap-2">
          <div className="w-full sm:w-60 relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <Input
              placeholder="Search rules, codes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 text-xs"
            />
          </div>

          {isAdmin && (
            <Button
              variant="primaryBlue"
              size="sm"
              className="gap-1.5 text-xs font-semibold shrink-0 cursor-pointer"
              onClick={onAddRule}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Rule</span>
            </Button>
          )}
        </div>
      </div>

      {/* Rules Grid */}
      {filteredRules.length === 0 ? (
        <Card className="p-12 text-center space-y-3">
          <BookOpen className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="text-sm font-semibold text-slate-800">
            {rules.length === 0
              ? 'No approved brand guidelines in this organisation yet'
              : 'No approved guidelines match your filter'}
          </p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {rules.length === 0
              ? 'Upload brand guideline manuals (.pdf, .docx) in the Source Documents tab to extract candidate rules, or add custom rules manually.'
              : 'Try adjusting your search query or select another category.'}
          </p>
          {rules.length === 0 ? (
            <div className="pt-2">
              <Button variant="primaryBlue" size="sm" onClick={onAddRule} className="gap-1.5">
                <Plus className="w-3.5 h-3.5" />
                <span>Add First Guideline Rule</span>
              </Button>
            </div>
          ) : (
            <Button variant="outline" size="sm" onClick={() => { setSearchQuery(''); setSelectedCategory('all'); }}>
              Reset Filters
            </Button>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRules.map((rule) => (
            <Card
              key={rule.id}
              className="p-5 hover:border-slate-300 transition-all shadow-xs flex flex-col justify-between"
            >
              <div className="space-y-3">
                {/* Header: Code, Category, SubCategory & Strictness */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="blue" className="text-[10px] font-mono font-bold">
                      {rule.code}
                    </Badge>
                    <Badge variant="neutral" className="text-[10px]">
                      {rule.category}
                    </Badge>
                    <span className="text-[11px] text-slate-500">
                      • {rule.subCategory}
                    </span>
                  </div>

                  <Badge
                    variant={rule.enforcementLevel === 'Strict' ? 'default' : 'secondary'}
                    className="text-[10px]"
                  >
                    {rule.enforcementLevel}
                  </Badge>
                </div>

                {/* Title & Description */}
                <div>
                  <h3 className="text-sm font-bold text-slate-900 leading-snug">
                    {rule.title}
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    {rule.description}
                  </p>
                </div>

                {/* Approved vs Prohibited Examples */}
                {rule.examples && (
                  <div className="space-y-1.5 pt-1 text-[11px]">
                    {rule.examples.approved && (
                      <div className="p-2 rounded bg-emerald-50/70 border border-emerald-200 text-emerald-950 flex items-start gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-emerald-800">Approved: </strong>
                          "{rule.examples.approved}"
                        </div>
                      </div>
                    )}
                    {rule.examples.prohibited && (
                      <div className="p-2 rounded bg-rose-50/70 border border-rose-200 text-rose-950 flex items-start gap-1.5">
                        <span className="text-rose-600 font-bold shrink-0">✕</span>
                        <div>
                          <strong className="text-rose-800">Prohibited: </strong>
                          "{rule.examples.prohibited}"
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Card Footer: Source Citation, Author & Edit/Delete Actions */}
              <div className="mt-4 pt-3 border-t border-border/80 flex items-center justify-between text-xs text-slate-400">
                <div className="truncate pr-2">
                  {rule.sourceDocument ? (
                    <span className="truncate block text-[11px] text-slate-500" title={`${rule.sourceDocument} (${rule.sourcePage || ''})`}>
                      Source: {rule.sourceDocument} {rule.sourcePage && `(${rule.sourcePage})`}
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-400">Manual Entry</span>
                  )}
                  <span className="text-[10px] text-slate-400">
                    Updated {rule.lastUpdated} by {rule.updatedBy}
                  </span>
                </div>

                {isAdmin && (
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-slate-400 hover:text-slate-800 cursor-pointer"
                      title="Edit Rule"
                      onClick={() => onEditRule(rule)}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-slate-400 hover:text-rose-600 cursor-pointer"
                      title="Delete Rule"
                      onClick={() => {
                        if (confirm(`Are you sure you want to delete rule ${rule.code}: "${rule.title}"?`)) {
                          onDeleteRule(rule.id)
                        }
                      }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
