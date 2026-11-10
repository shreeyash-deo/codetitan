import type { StudioFinding, StudioContentType, SupportingGuideline } from '@/types/reviewStudio'

export interface StudioPreset {
  id: string
  title: string
  contentType: StudioContentType
  rawContent: string
  description: string
  targetChannel: string
  findings: StudioFinding[]
}

export const supportingGuidelinesMap: Record<string, SupportingGuideline> = {
  'RULE-LEG-1.1': {
    id: 'sg-leg-1',
    code: 'RULE-LEG-1.1',
    title: 'Prohibited Superlatives & Unaudited Claims',
    category: 'Legal & Claims',
    description: 'Statutory financial regulations prohibit declaring absolute superlatives ("fastest in the world", "lowest fee anywhere") unless substantiated with contemporaneous third-party audit citations.',
    rationale: 'Protects the brand from FTC and FCA false advertising scrutiny and institutional skepticism.',
    enforcementLevel: 'Strict',
  },
  'RULE-VOC-2.4': {
    id: 'sg-voc-2',
    code: 'RULE-VOC-2.4',
    title: 'Official Product Terminology & Deprecated Names',
    category: 'Incorrect Terminology',
    description: 'Use canonical product naming conventions. "NovaPay Billing Suite" was officially deprecated in Q2 2026 and renamed to "NovaPay Subscriptions". "NovaPay Portal" is canonically "NovaPay Dashboard".',
    rationale: 'Eliminates customer confusion across enterprise integration documentation and contracts.',
    enforcementLevel: 'Strict',
  },
  'RULE-TON-3.2': {
    id: 'sg-ton-3',
    code: 'RULE-TON-3.2',
    title: 'Institutional Dignity & Collaborative Tone',
    category: 'Tone & Voice',
    description: 'Maintain an authoritative, partner-first voice. Avoid combative rhetoric such as "crushing legacy banks", "destroying paperwork", or "death of old banking".',
    rationale: 'NovaPay operates via Tier 1 banking partner rails; combative messaging damages clearing relationships.',
    enforcementLevel: 'Advisory',
  },
  'RULE-SEC-4.1': {
    id: 'sg-sec-4',
    code: 'RULE-SEC-4.1',
    title: 'Absolute Fraud & Risk Indemnity Restrictions',
    category: 'Incorrect Product Facts',
    description: 'Never promise "100% fraud immunity" or "zero chargebacks forever". Machine learning risk models mitigate risk up to verified statistical bounds (e.g. 82% reduction), but cannot guarantee zero anomalies.',
    rationale: 'Avoids contractual breach of warranty liabilities under merchant service agreements.',
    enforcementLevel: 'Strict',
  },
  'RULE-VIS-5.1': {
    id: 'sg-vis-5',
    code: 'RULE-VIS-5.1',
    title: 'Visual Identity & Logo Clearspace Invariance',
    category: 'Visual brand inconsistency',
    description: 'Marketing artboards must preserve minimum 24px exclusion zone around the NovaPay shield logomark and prohibit non-standard neon hex fills.',
    rationale: 'Ensures pristine readability and brand recognition across omnichannel display networks.',
    enforcementLevel: 'Strict',
  },
}

export const studioPresets: StudioPreset[] = [
  {
    id: 'preset-ad-campaign',
    title: 'Q4 Global Checkout Paid Ad Campaign',
    contentType: 'Advertisement',
    targetChannel: 'Google Display & LinkedIn Sponsored',
    description: 'High-volume paid creative announcing NovaPay’s checkout API upgrade.',
    rawContent: `Boost your e-commerce checkout conversions by 40% with NovaPay.

The world's fastest payment API is here, crushing legacy slow banks with sub-second clearing. Say goodbye to lost revenue — NovaPay Billing Suite provides 100% zero fraud guaranteed for high-volume enterprise stores.

Sign up in 5 minutes and eliminate checkout drop-off forever with zero upfront setup fees.`,
    findings: [
      {
        id: 'find-1',
        category: 'Unsupported claims',
        severity: 'critical',
        originalText: "The world's fastest payment API is here",
        explanation: 'Statutory financial advertising standards prohibit claiming "the world\'s fastest" without third-party audited benchmark citations.',
        supportingGuideline: supportingGuidelinesMap['RULE-LEG-1.1'],
        suggestedCorrection: 'Our lowest-latency payment API to date is here',
        confidence: 97,
        status: 'pending',
      },
      {
        id: 'find-2',
        category: 'Tone inconsistency',
        severity: 'warning',
        originalText: 'crushing legacy slow banks',
        explanation: 'Combative rhetoric violates Brand Dignity Rule 3.2. NovaPay partners with Tier 1 clearing institutions rather than disparaging them.',
        supportingGuideline: supportingGuidelinesMap['RULE-TON-3.2'],
        suggestedCorrection: 'modernizing legacy clearing infrastructure alongside banking partners',
        confidence: 92,
        status: 'pending',
      },
      {
        id: 'find-3',
        category: 'Incorrect terminology',
        severity: 'warning',
        originalText: 'NovaPay Billing Suite',
        explanation: '"NovaPay Billing Suite" was retired in Q2 2026. The canonical product name across all brand assets is "NovaPay Subscriptions".',
        supportingGuideline: supportingGuidelinesMap['RULE-VOC-2.4'],
        suggestedCorrection: 'NovaPay Subscriptions',
        confidence: 99,
        status: 'pending',
      },
      {
        id: 'find-4',
        category: 'Incorrect product facts',
        severity: 'critical',
        originalText: '100% zero fraud guaranteed',
        explanation: 'Product warranty rules forbid guaranteeing absolute zero fraud. Enterprise merchant SLAs define fraud mitigation velocity checks.',
        supportingGuideline: supportingGuidelinesMap['RULE-SEC-4.1'],
        suggestedCorrection: 'up to 82% fraud friction reduction via proactive ML velocity checks',
        confidence: 96,
        status: 'pending',
      },
      {
        id: 'find-5',
        category: 'Unsupported claims',
        severity: 'info',
        originalText: 'eliminate checkout drop-off forever',
        explanation: 'Absolute promise "forever" is unmeasurable in conversion analytics.',
        supportingGuideline: supportingGuidelinesMap['RULE-LEG-1.1'],
        suggestedCorrection: 'significantly minimize checkout friction across cross-border baskets',
        confidence: 88,
        status: 'pending',
      },
    ],
  },
  {
    id: 'preset-blog-post',
    title: 'Product Blog: Real-time Treasury Rails',
    contentType: 'Blog',
    targetChannel: 'NovaPay Engineering & Product Blog',
    description: 'Technical announcement regarding multi-currency liquidity management.',
    rawContent: `Today we are unveiling real-time treasury disbursements on NovaPay.

Enterprise CFOs can now manage multi-currency liquidity through the NovaPay Portal. With instant rails, cross-border payouts execute in under 3 seconds across 42 currencies. 

Unlike traditional wire transfers that hold capital hostage for 3-5 business days, our smart liquidity engine automatically matches FX routes with zero spread markup.`,
    findings: [
      {
        id: 'find-b1',
        category: 'Incorrect terminology',
        severity: 'warning',
        originalText: 'NovaPay Portal',
        explanation: 'Canonical brand terminology for the web management surface is "NovaPay Dashboard".',
        supportingGuideline: supportingGuidelinesMap['RULE-VOC-2.4'],
        suggestedCorrection: 'NovaPay Dashboard',
        confidence: 98,
        status: 'pending',
      },
      {
        id: 'find-b2',
        category: 'Unsupported claims',
        severity: 'critical',
        originalText: 'with zero spread markup',
        explanation: 'Treasury operations retain institutional wholesale spreads. Claiming zero spread contradicts NovaPay transparent pricing schedule 4.1.',
        supportingGuideline: supportingGuidelinesMap['RULE-LEG-1.1'],
        suggestedCorrection: 'with wholesale institutional interbank FX pricing',
        confidence: 95,
        status: 'pending',
      },
      {
        id: 'find-b3',
        category: 'Tone inconsistency',
        severity: 'info',
        originalText: 'hold capital hostage',
        explanation: 'Sensationalist imagery diverges from authoritative institutional fintech voice.',
        supportingGuideline: supportingGuidelinesMap['RULE-TON-3.2'],
        suggestedCorrection: 'require multi-day settlement windows',
        confidence: 89,
        status: 'pending',
      },
    ],
  },
  {
    id: 'preset-website-copy',
    title: 'Website Copy: Enterprise Subscriptions Hero Section',
    contentType: 'Website copy',
    targetChannel: 'novapay.io/enterprise-billing',
    description: 'High-conversion marketing landing page copy for B2B recurring billing.',
    rawContent: `Power your recurring revenue with the world's most resilient subscription platform.

NovaPay Subscriptions provides automated recurring invoices, localized payment methods in 130+ markets, and compliant tax calculations.

Trusted by leading SaaS enterprises to reduce churn and accelerate revenue operations.`,
    findings: [
      {
        id: 'find-w1',
        category: 'Unsupported claims',
        severity: 'warning',
        originalText: "the world's most resilient subscription platform",
        explanation: 'Superlative "most resilient" requires benchmark backing under advertising standards.',
        supportingGuideline: supportingGuidelinesMap['RULE-LEG-1.1'],
        suggestedCorrection: 'an enterprise-grade recurring billing and subscription engine',
        confidence: 94,
        status: 'pending',
      },
    ],
  },
]
