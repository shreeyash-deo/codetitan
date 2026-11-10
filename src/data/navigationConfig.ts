import {
  LayoutDashboard,
  FileCheck2,
  BookOpen,
  History,
  UserCheck,
  Settings,
} from 'lucide-react'
import type { NavItemConfig } from '@/types/navigation'

export const mainNavigationItems: NavItemConfig[] = [
  {
    id: 'overview',
    label: 'Overview',
    href: '/',
    icon: LayoutDashboard,
    description: 'Executive compliance health & telemetry',
  },
  {
    id: 'content-review',
    label: 'Content Review',
    href: '/content-review',
    icon: FileCheck2,
    badge: '3 pending',
    badgeVariant: 'accent',
    description: 'Real-time AI brand & legal scanner',
  },
  {
    id: 'brand-guidelines',
    label: 'Brand Guidelines',
    href: '/brand-guidelines',
    icon: BookOpen,
    badge: '4 active',
    description: 'Rule engine, voice rules & visual assets',
  },
  {
    id: 'review-history',
    label: 'Review History',
    href: '/review-history',
    icon: History,
    description: 'Audited assets, approvals & revisions',
  },
  {
    id: 'team-approvals',
    label: 'Team & Approvals',
    href: '/team-approvals',
    icon: UserCheck,
    description: 'Governance workflows & reviewer assignments',
  },
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Organization, model sensitivity & API keys',
  },
]
