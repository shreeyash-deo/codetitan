/**
 * BrandShield API TypeScript Interface Contracts
 * Compatible with FastAPI Pydantic models.
 */

// ============================================================================
// Core Domain Entities
// ============================================================================

export interface Brand {
  id: string
  name: string
  slug: string
  plan: 'Starter' | 'Growth' | 'Enterprise'
  complianceScore: number
  activeRulesCount: number
  brandColor: string
  createdAt?: string
  updatedAt?: string
}

export type GuidelineCategoryType =
  | 'Brand Voice'
  | 'Terminology'
  | 'Brand Facts'
  | 'Claims & Restrictions'
  | 'Visual Identity'

export type EnforcementLevelType = 'Strict' | 'Advisory'

export interface BrandGuideline {
  id: string
  code: string // e.g. BV-01, TM-02
  category: GuidelineCategoryType
  subCategory: string
  title: string
  description: string
  enforcementLevel: EnforcementLevelType
  approvedExample?: string
  prohibitedExample?: string
  sourceDocument?: string
  sourcePage?: string
  lastUpdated: string
  updatedBy: string
}

export interface ExtractedRule {
  id: string
  category: GuidelineCategoryType
  subCategory: string
  title: string
  extractedText: string
  rationale: string
  sourceDocument: string
  sourceSection: string
  confidence: number // 0-100 float or int
  dateExtracted: string
  suggestedEnforcement: EnforcementLevelType
  status: 'pending' | 'approved' | 'rejected'
}

export interface SourceDocument {
  id: string
  name: string
  format: 'PDF' | 'DOCX'
  size: string
  pages: number
  uploadedAt: string
  uploadedBy: string
  status: 'extracted' | 'processing' | 'indexed'
  extractedCandidatesCount: number
  approvedRulesCount: number
  fileUrl?: string
}

// ============================================================================
// Content Review & Analysis
// ============================================================================

export type ChannelType =
  | 'Social'
  | 'Blog'
  | 'Product Landing'
  | 'Email Campaign'
  | 'Ad Creative'
  | 'Press Release'
  | 'Other'

export interface ReviewRequest {
  title: string
  contentType: string
  channel: ChannelType
  content: string
  strictness: 'advisory' | 'standard' | 'strict'
  activeCategories?: string[]
  activeGuidelines?: string[]
  documentId?: string
}

export interface CorrectionSuggestion {
  id: string
  originalSnippet: string
  suggestedReplacement: string
  rationale: string
  confidence: number
}

export interface ComplianceFinding {
  id: string
  category: string
  severity: 'critical' | 'moderate' | 'minor'
  originalText: string
  explanation: string
  supportingGuidelineCode: string
  supportingGuidelineTitle: string
  suggestedCorrection: string
  confidence: number
  resolved?: boolean
}

export interface ReviewResult {
  id: string
  title: string
  contentType: string
  channel: ChannelType
  overallScore: number
  issuesCount: number
  status: 'approved' | 'in_review' | 'flagged' | 'rejected' | 'rules_unavailable'
  hasApprovedRules?: boolean
  summary: string
  contentPreview: string
  findings: ComplianceFinding[]
  analyzedAt: string
}

// ============================================================================
// Approvals & Workflow
// ============================================================================

export type ApprovalStatusType =
  | 'approved'
  | 'pending'
  | 'needs_revision'
  | 'critical_issues'

export interface ReviewComment {
  id: string
  authorName: string
  authorRole: string
  authorAvatar?: string
  text: string
  timestamp: string
}

export interface ApprovalTimelineStage {
  id: string
  stage:
    | 'Content submitted'
    | 'AI review completed'
    | 'Suggestions applied'
    | 'Approval requested'
    | 'Reviewer decision'
    | 'Final approval'
  actorName: string
  actorRole: string
  timestamp: string
  note?: string
  status: 'completed' | 'current' | 'pending'
}

export interface ApprovalRequest {
  id: string
  reviewId: string
  title: string
  contentType: string
  submittedBy: {
    name: string
    role: string
    email: string
    avatar?: string
  }
  assignedReviewer: {
    name: string
    role: string
    email: string
    avatar?: string
  }
  score: number
  status: ApprovalStatusType
  reviewDate: string
  contentExcerpt: string
  commentsCount: number
}

// ============================================================================
// Review History & Ledger
// ============================================================================

export interface ReviewHistory {
  id: string
  title: string
  contentType: string
  channel: ChannelType
  submittedBy: {
    name: string
    role: string
    email: string
    avatar?: string
  }
  assignedReviewer: {
    name: string
    role: string
    email: string
    avatar?: string
  }
  score: number
  violationsCount: number
  reviewDate: string
  approvalStatus: ApprovalStatusType
  originalContent: string
  correctedContent: string
  findings: ComplianceFinding[]
  acceptedSuggestionsCount: number
  rejectedSuggestionsCount: number
  comments: ReviewComment[]
  timeline: ApprovalTimelineStage[]
}

// ============================================================================
// Generic API Transport Envelopes
// ============================================================================

export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
  timestamp: string
}

export interface ApiError {
  message: string
  detail?: string
  statusCode: number
}
