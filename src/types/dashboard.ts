export type ActivityType =
  | 'content_uploaded'
  | 'review_completed'
  | 'correction_accepted'
  | 'approval_requested'
  | 'content_approved'

export interface ActivityItem {
  id: string
  type: ActivityType
  title: string
  description: string
  actor: {
    name: string
    avatar?: string
    role?: string
  }
  timestamp: string
  targetId?: string
  status?: string
}

export interface IssueBreakdownItem {
  category: string
  count: number
  percentage: number
  severity: 'critical' | 'moderate' | 'minor'
  color: string
  description: string
}

export interface BrandGuidelinesTelemetry {
  approvedRules: number
  pendingRules: number
  totalRules: number
  lastUpdated: string
  knowledgeExtraction: {
    status: 'Synced & Indexed' | 'Syncing' | 'Needs Re-indexing'
    version: string
    indexedChunks: number
    lastRun: string
  }
}
