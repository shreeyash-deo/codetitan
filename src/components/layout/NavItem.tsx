import React from 'react'
import { NavLink } from 'react-router-dom'
import type { NavItemConfig } from '@/types/navigation'
import { cn } from '@/lib/utils'

interface NavItemProps {
  item: NavItemConfig
  collapsed?: boolean
  onClick?: () => void
}

export const NavItem: React.FC<NavItemProps> = ({ item, collapsed = false, onClick }) => {
  const Icon = item.icon

  return (
    <NavLink
      to={item.href}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center rounded-md text-xs font-medium transition-all duration-150 select-none outline-none',
          collapsed ? 'justify-center w-10 h-10 mx-auto' : 'w-full px-2.5 py-2 gap-2.5',
          isActive
            ? 'bg-blue-600 text-white shadow-xs font-semibold'
            : 'text-slate-300 hover:text-white hover:bg-slate-800/80 active:bg-slate-800'
        )
      }
      title={collapsed ? `${item.label}${item.badge ? ` (${item.badge})` : ''}` : undefined}
    >
      {({ isActive }) => (
        <>
          <Icon
            className={cn(
              'shrink-0 transition-transform duration-150 group-hover:scale-105',
              collapsed ? 'w-4 h-4' : 'w-4 h-4',
              isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
            )}
          />

          {!collapsed && (
            <div className="flex items-center justify-between w-full min-w-0">
              <span className="truncate">{item.label}</span>
              {item.badge && (
                <span
                  className={cn(
                    'text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0 ml-1.5 transition-colors',
                    isActive
                      ? 'bg-white/20 text-white'
                      : item.badgeVariant === 'accent'
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      : 'bg-slate-800 text-slate-400 border border-slate-700/60'
                  )}
                >
                  {item.badge}
                </span>
              )}
            </div>
          )}

          {collapsed && item.badge && (
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-blue-500 ring-2 ring-[#0B1220]" />
          )}
        </>
      )}
    </NavLink>
  )
}
