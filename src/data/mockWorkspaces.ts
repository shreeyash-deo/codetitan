import type { Workspace } from '@/types/workspace'

export const mockWorkspaces: Workspace[] = [
  {
    id: 'ws-novapay',
    name: 'NovaPay',
    slug: 'novapay-global',
    plan: 'Enterprise',
    brandCount: 3,
    complianceScore: 87,
    color: '#2563EB',
  },
  {
    id: 'ws-acme',
    name: 'Acme Global Corp',
    slug: 'acme-global',
    plan: 'Enterprise',
    brandCount: 4,
    complianceScore: 94,
    color: '#059669',
  },
  {
    id: 'ws-vertex',
    name: 'Vertex Ventures',
    slug: 'vertex-ventures',
    plan: 'Growth',
    brandCount: 2,
    complianceScore: 91,
    color: '#7C3AED',
  },
]
