import type { LucideIcon } from 'lucide-react'

export interface NavItemConfig {
  id: string
  label: string
  href: string
  icon: LucideIcon
  badge?: string | number
  badgeVariant?: 'default' | 'accent' | 'warning'
  description?: string
}

export interface BreadcrumbItem {
  label: string
  href?: string
  current?: boolean
}
