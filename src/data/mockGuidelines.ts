import type { BrandGuideline } from '@/types/guidelines'

export const mockGuidelines: BrandGuideline[] = [
  {
    id: 'bg-voice',
    title: 'Brand Tone of Voice & Lexicon',
    category: 'Voice & Tone',
    ruleCount: 18,
    lastUpdated: 'Yesterday, 14:20',
    status: 'active',
    description: 'Guidelines on brand vocabulary, authoritative yet accessible language, banned buzzwords, and tone calibration.',
    enforcementLevel: 'Strict',
  },
  {
    id: 'bg-logo',
    title: 'Master Identity, Clearspace & Marks',
    category: 'Logo & Imagery',
    ruleCount: 12,
    lastUpdated: '3 days ago',
    status: 'active',
    description: 'Minimum isolation zones, monochromatic variants, lockups, and forbidden color adaptations.',
    enforcementLevel: 'Strict',
  },
  {
    id: 'bg-legal',
    title: 'Statutory Claims & Legal Disclaimers',
    category: 'Legal & Claims',
    ruleCount: 9,
    lastUpdated: 'Oct 28, 2026',
    status: 'active',
    description: 'Mandatory disclaimer disclosures for AI features, security claims, and SLA benchmark guarantees.',
    enforcementLevel: 'Strict',
  },
  {
    id: 'bg-color',
    title: 'Color Palette & Accessible Contrast Ratios',
    category: 'Color & Typography',
    ruleCount: 14,
    lastUpdated: 'Oct 15, 2026',
    status: 'active',
    description: 'Primary deep navy tokens, secondary blues, WCAG AAA compliant background/foreground combinations.',
    enforcementLevel: 'Advisory',
  },
]
