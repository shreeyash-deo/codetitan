import React, { useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import {
  Bell,
  Search,
  Menu,
  ChevronRight,
  Shield,
  Sparkles,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useToast } from '@/context/ToastContext'

interface HeaderProps {
  onMobileMenuToggle: () => void
}

const routeTitles: Record<string, { title: string; category?: string }> = {
  '/': { title: 'Overview', category: 'Platform' },
  '/content-review': { title: 'Content Review', category: 'Auditing' },
  '/brand-guidelines': { title: 'Brand Guidelines', category: 'Governance' },
  '/review-history': { title: 'Review History', category: 'Compliance' },
  '/team-approvals': { title: 'Team & Approvals', category: 'Workflow' },
  '/settings': { title: 'Settings', category: 'Administration' },
}

export const Header: React.FC<HeaderProps> = ({ onMobileMenuToggle }) => {
  const location = useLocation()
  const { currentWorkspace } = useWorkspace()
  const { info, success } = useToast()
  const [unreadNotifications, setUnreadNotifications] = useState(3)

  const currentRouteInfo = routeTitles[location.pathname] || {
    title: 'BrandShield',
    category: 'Platform',
  }

  const handleCommandPalette = () => {
    info('Press ⌘K or use the search bars across Review Studio, Guidelines, and History to quickly locate assets.', 'Quick Navigation')
  }

  return (
    <header className="h-14 border-b border-border bg-white/95 backdrop-blur supports-backdrop-blur:bg-white/80 sticky top-0 z-20 px-4 sm:px-6 flex items-center justify-between gap-4 select-none">
      {/* Left: Mobile Toggle + Breadcrumbs */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMobileMenuToggle}
          className="lg:hidden p-1.5 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          aria-label="Open mobile navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Breadcrumb Navigation */}
        <nav className="flex items-center space-x-1.5 text-xs text-slate-500 min-w-0">
          <Link
            to="/"
            className="hover:text-slate-900 transition-colors flex items-center gap-1 font-medium truncate"
          >
            <Shield className="w-3.5 h-3.5 text-blue-600 shrink-0" />
            <span className="hidden sm:inline">{currentWorkspace?.name || 'Organisation'}</span>
          </Link>

          <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />

          {currentRouteInfo.category && (
            <>
              <span className="hidden md:inline text-slate-400">
                {currentRouteInfo.category}
              </span>
              <ChevronRight className="hidden md:inline w-3.5 h-3.5 text-slate-400 shrink-0" />
            </>
          )}

          <span className="font-semibold text-slate-900 truncate">
            {currentRouteInfo.title}
          </span>
        </nav>
      </div>

      {/* Right: Quick Search, Notifications & Contextual Actions */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
        {/* Search trigger */}
        <button
          onClick={handleCommandPalette}
          className="hidden md:flex items-center gap-2 h-8 px-2.5 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-400 hover:text-slate-700 hover:border-slate-300 transition-all shadow-xs"
        >
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span>Search assets or rules...</span>
          <kbd className="hidden lg:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-white border border-slate-200 rounded">
            ⌘K
          </kbd>
        </button>

        {/* Notifications Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className="relative text-slate-600 hover:text-slate-900"
              aria-label="View notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadNotifications > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-600 px-1 text-[9px] font-bold text-white ring-2 ring-white">
                  {unreadNotifications}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-80 p-2 shadow-xl">
            <div className="flex items-center justify-between px-2 py-1.5">
              <DropdownMenuLabel className="p-0 text-xs font-semibold text-slate-900">
                Compliance Notifications
              </DropdownMenuLabel>
              {unreadNotifications > 0 && (
                <button
                  onClick={() => {
                    setUnreadNotifications(0)
                    success('All compliance notifications marked as read.', 'Notifications')
                  }}
                  className="text-[11px] text-blue-600 hover:underline"
                >
                  Mark all as read
                </button>
              )}
            </div>

            <DropdownMenuSeparator />

            <div className="space-y-1 py-1">
              <DropdownMenuItem className="flex flex-col items-start gap-1 p-2 rounded-md hover:bg-slate-50 cursor-pointer">
                <div className="flex items-center justify-between w-full">
                  <span className="text-xs font-medium text-slate-800 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                    Logo Violation Flagged
                  </span>
                  <span className="text-[10px] text-slate-400">45m ago</span>
                </div>
                <p className="text-[11px] text-slate-500 leading-tight">
                  Paid Social Banner #4 failed clearspace isolation threshold.
                </p>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex flex-col items-start gap-1 p-2 rounded-md hover:bg-slate-50 cursor-pointer">
                <div className="flex items-center justify-between w-full">
                  <span className="text-xs font-medium text-slate-800 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Review Approved
                  </span>
                  <span className="text-[10px] text-slate-400">2h ago</span>
                </div>
                <p className="text-[11px] text-slate-500 leading-tight">
                  Q4 Keynote transcript marked 100% compliant by Marcus Vance.
                </p>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex flex-col items-start gap-1 p-2 rounded-md hover:bg-slate-50 cursor-pointer">
                <div className="flex items-center justify-between w-full">
                  <span className="text-xs font-medium text-slate-800 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    Guideline Updated
                  </span>
                  <span className="text-[10px] text-slate-400">1d ago</span>
                </div>
                <p className="text-[11px] text-slate-500 leading-tight">
                  Legal disclaimers rule #9 updated for EU AI Act compliance.
                </p>
              </DropdownMenuItem>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Contextual Action: Quick Audit / New Review */}
        <Link to="/content-review">
          <Button
            variant="primaryBlue"
            size="sm"
            className="flex items-center gap-1.5 font-medium shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Review</span>
          </Button>
        </Link>
      </div>
    </header>
  )
}
