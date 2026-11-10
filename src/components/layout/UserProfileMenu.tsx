import React from 'react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { mockUser } from '@/data/mockUser'
import { useToast } from '@/context/ToastContext'
import {
  User,
  Shield,
  KeyRound,
  LogOut,
  Bell,
  CheckCircle2,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface UserProfileMenuProps {
  collapsed?: boolean
}

export const UserProfileMenu: React.FC<UserProfileMenuProps> = ({ collapsed = false }) => {
  const { info, success } = useToast()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            'flex items-center gap-2.5 rounded-lg p-1.5 transition-colors text-left w-full',
            'hover:bg-slate-800/80 border border-transparent hover:border-white/5 outline-none focus-visible:ring-1 focus-visible:ring-blue-500',
            collapsed ? 'justify-center' : 'justify-between'
          )}
          title={collapsed ? `${mockUser.name} (${mockUser.role})` : undefined}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="relative shrink-0">
              <Avatar className="w-7 h-7 rounded-full ring-1 ring-white/10">
                <AvatarImage src={mockUser.avatarUrl} alt={mockUser.name} />
                <AvatarFallback className="bg-blue-900 text-blue-200 text-xs">
                  SC
                </AvatarFallback>
              </Avatar>
              <span className="absolute bottom-0 right-0 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-[#0B1220]" />
            </div>

            {!collapsed && (
              <div className="flex flex-col min-w-0 text-left">
                <span className="text-xs font-medium text-slate-200 truncate leading-tight">
                  {mockUser.name}
                </span>
                <span className="text-[10px] text-slate-400 truncate">
                  {mockUser.role}
                </span>
              </div>
            )}
          </div>
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align={collapsed ? 'start' : 'end'}
        side={collapsed ? 'right' : 'top'}
        className="w-56 bg-slate-900 text-slate-200 border-slate-800 p-1.5 shadow-2xl"
      >
        <DropdownMenuLabel className="px-2 py-1.5">
          <div className="text-xs font-semibold text-white">{mockUser.name}</div>
          <div className="text-[10px] text-slate-400 font-normal truncate">{mockUser.email}</div>
          <div className="mt-1.5 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-900/50 text-blue-300 text-[10px] border border-blue-800/60 font-medium">
            <CheckCircle2 className="w-2.5 h-2.5" />
            Verified Brand Lead
          </div>
        </DropdownMenuLabel>

        <DropdownMenuSeparator className="bg-slate-800" />

        <DropdownMenuItem
          onClick={() => info(`Logged in as ${mockUser.name}. Multi-factor biometric verified.`, 'Profile Info')}
          className="flex items-center gap-2 text-xs py-1.5 px-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded cursor-pointer"
        >
          <User className="w-3.5 h-3.5 text-slate-400" />
          <span>My Profile & Preferences</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={() => info('Notification dispatch configured for email & #brand-governance Slack.', 'Alert Rules')}
          className="flex items-center gap-2 text-xs py-1.5 px-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded cursor-pointer"
        >
          <Bell className="w-3.5 h-3.5 text-slate-400" />
          <span>Notification Rules</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={() => info('Role: Brand Lead with Tier 3 final publishing clearance.', 'RBAC Authority')}
          className="flex items-center gap-2 text-xs py-1.5 px-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded cursor-pointer"
        >
          <Shield className="w-3.5 h-3.5 text-slate-400" />
          <span>Governance Permissions</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={() => info('Production API Key: pk_live_brandshield_novapay_*** active.', 'API Keys')}
          className="flex items-center gap-2 text-xs py-1.5 px-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded cursor-pointer"
        >
          <KeyRound className="w-3.5 h-3.5 text-slate-400" />
          <span>Developer API Keys</span>
        </DropdownMenuItem>

        <DropdownMenuSeparator className="bg-slate-800" />

        <DropdownMenuItem
          onClick={() => success('Signed out safely. Session token invalidated.', 'Session Ended')}
          className="flex items-center gap-2 text-xs py-1.5 px-2 text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 rounded cursor-pointer"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
