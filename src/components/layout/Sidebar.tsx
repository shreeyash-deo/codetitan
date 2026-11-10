import React from 'react'
import { BrandShieldLogo } from './BrandShieldLogo'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import { NavItem } from './NavItem'
import { UserProfileMenu } from './UserProfileMenu'
import { mainNavigationItems } from '@/data/navigationConfig'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useToast } from '@/context/ToastContext'
import { PanelLeftClose, PanelLeft, Sparkles, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  onItemClick?: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggleCollapse,
  onItemClick,
}) => {
  const { info } = useToast()
  const { currentWorkspace } = useWorkspace()
  const isAdmin = (currentWorkspace?.role || '').toLowerCase() === 'admin'

  const visibleNavItems = mainNavigationItems.filter((item) => {
    if (item.id === 'settings' && !isAdmin) return false
    return true
  })

  return (
    <aside
      className={cn(
        'relative flex flex-col h-full bg-[#0B1220] border-r border-[#152238] select-none transition-all duration-200 z-30 shrink-0 text-slate-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Top Header: Logo & Collapse Trigger */}
      <div
        className={cn(
          'flex items-center h-14 border-b border-[#152238] px-3',
          collapsed ? 'justify-center' : 'justify-between'
        )}
      >
        <BrandShieldLogo collapsed={collapsed} />

        {!collapsed && (
          <button
            onClick={onToggleCollapse}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Workspace Switcher */}
      <div className="p-2 border-b border-[#152238]/80">
        <WorkspaceSwitcher collapsed={collapsed} />
      </div>

      {/* Main Navigation */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        <div className={cn('px-2 pb-1.5', collapsed && 'hidden')}>
          <span className="text-[10px] font-semibold tracking-wider uppercase text-slate-400">
            Platform
          </span>
        </div>

        <nav className="space-y-1">
          {visibleNavItems.map((item) => (
            <NavItem
              key={item.id}
              item={item}
              collapsed={collapsed}
              onClick={onItemClick}
            />
          ))}
        </nav>

        {/* AI Compliance Engine Status Widget */}
        {!collapsed && (
          <div className="mt-6 mx-1 p-3 rounded-lg bg-[#0F172A] border border-slate-800 text-slate-300">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                <span>AI Sentinel active</span>
              </div>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
            </div>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Auto-checking text, tone, & visual guidelines across 4 channels.
            </p>
          </div>
        )}
      </div>

      {/* Bottom Footer: Secondary Links & User Profile */}
      <div className="p-2 border-t border-[#152238] space-y-1 bg-[#090F1C]">
        {collapsed ? (
          <div className="flex justify-center pb-2">
            <button
              onClick={onToggleCollapse}
              className="p-1.5 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <PanelLeft className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between px-2 py-1 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              All systems nominal
            </span>
            <button
              onClick={() => info('BrandShield v2.4 Knowledge Engine & Governance Documentation is up to date.', 'System Docs')}
              className="hover:text-slate-200 transition-colors flex items-center gap-1"
            >
              <HelpCircle className="w-3 h-3" />
              Docs
            </button>
          </div>
        )}

        <UserProfileMenu collapsed={collapsed} />
      </div>
    </aside>
  )
}
