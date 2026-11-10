export type StudioContentType =
  | 'Social media'
  | 'Advertisement'
  | 'Blog'
  | 'Email'
  | 'Website copy'
  | 'Other'

export type StudioSeverity = 'critical' | 'warning' | 'info'

export type StudioCategory =
  | 'Tone inconsistency'
  | 'Incorrect terminology'
  | 'Unsupported claims'
  | 'Incorrect product facts'
  | 'Visual brand inconsistency'

export type StrictnessLevel = 'advisory' | 'standard' | 'strict'

export interface SupportingGuideline {
  id: string
  code: string
  title: string
  category: string
  description: string
  rationale: string
  enforcementLevel: 'Strict' | 'Advisory'
}

export interface StudioFinding {
  id: string
  category: StudioCategory
  severity: StudioSeverity
  originalText: string
  explanation: string
  supportingGuideline: SupportingGuideline
  suggestedCorrection: string
  confidence: number // 0-100
  status: 'pending' | 'accepted' | 'rejected' | 'manual'
  manualReplacement?: string
}

export interface AnalysisStageInfo {
  id: number
  name: string
  description: string
  status: 'pending' | 'active' | 'completed'
}

export interface ReviewStudioConfig {
  contentType: StudioContentType
  strictness: StrictnessLevel
  activeCategories: StudioCategory[]
  activeGuidelines: string[]
}
