import type { MetricSummary } from '@/types/review'
import type { ActivityItem, IssueBreakdownItem, BrandGuidelinesTelemetry } from '@/types/dashboard'

export const mockDashboardMetrics: MetricSummary[] = [
  {
    label: 'Brand Compliance Score',
    value: '87/100',
    change: '+4.2 pts',
    isPositive: true,
    trendDescription: 'vs. 30d baseline (82.8)',
    targetRoute: '/brand-guidelines',
  },
  {
    label: 'Content Reviewed',
    value: '124',
    change: '+18%',
    isPositive: true,
    trendDescription: 'assets audited this month',
    targetRoute: '/review-history',
  },
  {
    label: 'Pending Approvals',
    value: '8',
    change: '4 urgent',
    isPositive: false,
    trendDescription: 'awaiting brand lead sign-off',
    targetRoute: '/team-approvals',
  },
  {
    label: 'Critical Issues',
    value: '3',
    change: '-2 from yesterday',
    isPositive: true,
    trendDescription: 'requires immediate remediation',
    targetRoute: '/content-review',
  },
]

export const mockIssuesBreakdown: IssueBreakdownItem[] = [
  {
    category: 'Tone inconsistencies',
    count: 14,
    percentage: 38,
    severity: 'moderate',
    color: '#3B82F6', // Blue
    description: 'Informal colloquialisms, aggressive sales rhetoric, or passive voice deviations.',
  },
  {
    category: 'Incorrect brand terminology',
    count: 11,
    percentage: 30,
    severity: 'minor',
    color: '#6366F1', // Indigo
    description: 'Deprecated product naming, miscapitalized acronyms, or non-standard tier terms.',
  },
  {
    category: 'Unsupported claims',
    count: 7,
    percentage: 19,
    severity: 'critical',
    color: '#EF4444', // Red/Rose
    description: 'Unsubstantiated performance claims, missing disclaimer footnotes, or superlative comparisons.',
  },
  {
    category: 'Visual inconsistencies',
    count: 5,
    percentage: 13,
    severity: 'moderate',
    color: '#F59E0B', // Amber
    description: 'Logo clearspace violations, unapproved gradient overlays, or low-contrast text.',
  },
]

export const mockRecentActivity: ActivityItem[] = [
  {
    id: 'act-01',
    type: 'content_approved',
    title: 'Content approved',
    description: 'Marcus Vance marked "NovaPay Instant Cross-Border Payouts" as 100% compliant.',
    actor: {
      name: 'Marcus Vance',
      role: 'Growth Marketing Lead',
      avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
    },
    timestamp: '18 mins ago',
    targetId: 'rev-01',
  },
  {
    id: 'act-02',
    type: 'correction_accepted',
    title: 'Correction accepted',
    description: 'Elena Rostova applied AI remediation to "Q4 Global Checkout Paid Ads" (isolation zone padding).',
    actor: {
      name: 'Elena Rostova',
      role: 'Creative Designer',
      avatar: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=100&auto=format&fit=crop&q=80',
    },
    timestamp: '42 mins ago',
    targetId: 'rev-02',
  },
  {
    id: 'act-03',
    type: 'approval_requested',
    title: 'Approval requested',
    description: 'David Kim routed "Enterprise Billing & Subscriptions Docs" for Tier 2 legal validation.',
    actor: {
      name: 'David Kim',
      role: 'Product Marketing Manager',
      avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80',
    },
    timestamp: '2 hours ago',
    targetId: 'rev-03',
  },
  {
    id: 'act-04',
    type: 'review_completed',
    title: 'Review completed',
    description: 'AI Sentinel scanned "Merchant Onboarding Welcome Email Series" with score 97/100.',
    actor: {
      name: 'BrandShield AI',
      role: 'Automated Sentinel',
    },
    timestamp: '5 hours ago',
    targetId: 'rev-04',
  },
  {
    id: 'act-05',
    type: 'content_uploaded',
    title: 'Content uploaded',
    description: 'Sarah Chen ingested "Series C Extension Press Release" draft from Notion workspace.',
    actor: {
      name: 'Sarah Chen',
      role: 'VP Communications',
      avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
    },
    timestamp: 'Yesterday at 5:12 PM',
    targetId: 'rev-05',
  },
]

export const mockGuidelinesTelemetry: BrandGuidelinesTelemetry = {
  approvedRules: 48,
  pendingRules: 5,
  totalRules: 53,
  lastUpdated: 'Today at 2:15 PM',
  knowledgeExtraction: {
    status: 'Synced & Indexed',
    version: 'v2.4.1',
    indexedChunks: 412,
    lastRun: '14 mins ago',
  },
}
