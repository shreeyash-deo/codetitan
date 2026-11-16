import { ComplianceFinding } from './api'

export interface ContentVersionSummary {
  id: number
  reviewId: number
  versionNumber: number
  contentHash: string
  complianceScore: number
  status: string
  auditStatus: string
  findingsCount: number
  ruleSetVersion?: string | null
  summary?: string | null
  changeDescription?: string | null
  authorId?: number | null
  authorName?: string | null
  versionState?: 'saved_draft' | 'audited' | 'submitted' | 'approved' | 'changes_requested' | string | null
  isCurrent?: boolean
  isOriginal?: boolean
  createdAt: string
}

export interface ContentVersionDetail extends ContentVersionSummary {
  content: string
  findings: ComplianceFinding[]
}

export interface DiffHunk {
  changeType: 'added' | 'removed' | 'unchanged'
  change_type?: 'added' | 'removed' | 'unchanged'
  content: string
  oldStart?: number | null
  oldLines?: number | null
  newStart?: number | null
  newLines?: number | null
}

export interface FindingDelta {
  resolved: ComplianceFinding[]
  new: ComplianceFinding[]
  persistent: ComplianceFinding[]
}

export interface VersionComparison {
  reviewId: number
  sourceVersion: ContentVersionSummary
  targetVersion: ContentVersionSummary
  scoreBefore: number
  scoreAfter: number
  scoreDelta: number
  auditStatusBefore: string
  auditStatusAfter: string
  textDiff: DiffHunk[]
  rawDiff: string
  findingsDelta: FindingDelta
  sourceContent?: string
  targetContent?: string
  source_content?: string
  target_content?: string
}
