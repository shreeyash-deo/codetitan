import type { ComplianceStatus, DetectedIssue } from './review'
import type { ComplianceFinding } from './api'

export type ApprovalFilter =
  | 'all'
  | 'approved'
  | 'pending'
  | 'needs_revision'
  | 'critical_issues'

export interface ReviewerComment {
  id: string
  authorName: string
  authorAvatar?: string
  authorRole: string
  text: string
  timestamp: string
}

export interface TimelineEvent {
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

export interface HistoricalReviewRecord {
  id: string
  title: string
  contentType: string
  channel: 'Blog' | 'Social' | 'Ad Creative' | 'Product Landing' | 'Email Campaign' | 'Press Release'
  submittedBy: {
    name: string
    avatar?: string
    role: string
    email: string
  }
  assignedReviewer: {
    name: string
    avatar?: string
    role: string
    email: string
  }
  score: number // 0-100
  auditStatus?: 'verified' | 'pending' | 'stale' | 'failed' | 'rules_unavailable' | string
  auditedAt?: string
  auditedContentHash?: string
  violationsCount: number
  reviewDate: string
  approvalStatus: 'approved' | 'pending' | 'needs_revision' | 'critical_issues'
  originalContent: string
  correctedContent: string
  findings: (DetectedIssue | ComplianceFinding | any)[]
  acceptedSuggestionsCount: number
  rejectedSuggestionsCount: number
  comments: ReviewerComment[]
  timeline: TimelineEvent[]
}
