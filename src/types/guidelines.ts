export type GuidelineCategory =
  | 'Brand Voice'
  | 'Terminology'
  | 'Brand Facts'
  | 'Claims & Restrictions'
  | 'Visual Identity'

export type EnforcementLevel = 'Strict' | 'Advisory'

export interface BrandGuideline {
  id: string
  title: string
  category: 'Voice & Tone' | 'Logo & Imagery' | 'Legal & Claims' | 'Color & Typography'
  ruleCount: number
  lastUpdated: string
  status: 'active' | 'draft' | 'archived'
  description: string
  enforcementLevel: 'Strict' | 'Advisory' | 'Informational'
}

export interface ApprovedRule {
  id: string
  code: string
  category: GuidelineCategory
  subCategory: string
  title: string
  description: string
  enforcementLevel: EnforcementLevel
  examples?: {
    approved: string
    prohibited: string
  }
  sourceDocument?: string
  sourcePage?: string
  lastUpdated: string
  updatedBy: string
}

export interface PendingCandidateRule {
  id: string
  category: GuidelineCategory
  subCategory: string
  title: string
  extractedText: string
  rationale: string
  sourceDocument: string
  sourceSection: string
  confidence: number // 0-100
  dateExtracted: string
  suggestedEnforcement: EnforcementLevel
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
}

export interface BrandColorSwatch {
  name: string
  hex: string
  rgb: string
  cmyk: string
  usage: string
  wcagContrast: string
}

export interface BrandVoiceSummary {
  primaryTone: string
  description: string
  pillars: {
    trait: string
    positive: string
    negative: string
  }[]
  readingLevel: string
}

export interface BrandIdentitySummary {
  logoClearspace: string
  minimumLogoWidth: string
  primaryTypeface: string
  monoTypeface: string
  colors: BrandColorSwatch[]
}
