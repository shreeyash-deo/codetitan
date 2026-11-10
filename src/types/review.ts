export type ComplianceStatus = 'approved' | 'in_review' | 'flagged' | 'rejected'

export type IssueCategory =
  | 'Tone inconsistencies'
  | 'Incorrect brand terminology'
  | 'Unsupported claims'
  | 'Visual inconsistencies'

export interface DetectedIssue {
  id: string
  category: IssueCategory
  severity: 'critical' | 'moderate' | 'minor'
  snippet: string
  explanation: string
  suggestion: string
  resolved?: boolean
}

export interface ReviewItem {
  id: string
  title: string
  channel: 'Social' | 'Blog' | 'Product Landing' | 'Email Campaign' | 'Ad Creative' | 'Press Release'
  contentType: string
  author: {
    name: string
    avatar?: string
    role?: string
    email?: string
  }
  score: number // 0-100
  status: ComplianceStatus
  issuesDetected: number
  submittedAt: string
  date: string
  brandGuidelineId: string
  summary: string
  contentPreview?: string
  issues?: DetectedIssue[]
}

export interface MetricSummary {
  label: string
  value: string | number
  change?: string
  isPositive?: boolean
  trendDescription?: string
  targetRoute?: string
}
