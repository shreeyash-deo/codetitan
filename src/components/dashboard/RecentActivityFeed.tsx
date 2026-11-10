import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  UploadCloud,
  CheckCircle2,
  Sparkles,
  GitPullRequest,
  CheckCheck,
  Clock,
  FileText,
  AlertCircle,
  MessageSquare,
  ShieldAlert,
} from 'lucide-react'
import type { DashboardActivityItem } from '@/services/brandService'

interface RecentActivityFeedProps {
  activity?: DashboardActivityItem[]
  onSelectActivityTarget?: (targetId: string) => void
}

function getActivityConfig(action: string) {
  const norm = action.toLowerCase()
  if (norm.includes('upload') || norm.includes('guideline')) {
    return {
      icon: UploadCloud,
      color: 'text-blue-600',
      bg: 'bg-blue-50 border-blue-200',
    }
  }
  if (norm.includes('audit') || norm.includes('scan') || norm.includes('review completed')) {
    return {
      icon: Sparkles,
      color: 'text-purple-600',
      bg: 'bg-purple-50 border-purple-200',
    }
  }
  if (norm.includes('approv') && !norm.includes('request')) {
    return {
      icon: CheckCircle2,
      color: 'text-emerald-700',
      bg: 'bg-emerald-100 border-emerald-300',
    }
  }
  if (norm.includes('request') || norm.includes('in_review')) {
    return {
      icon: GitPullRequest,
      color: 'text-amber-600',
      bg: 'bg-amber-50 border-amber-200',
    }
  }
  if (norm.includes('change') || norm.includes('revision')) {
    return {
      icon: ShieldAlert,
      color: 'text-rose-600',
      bg: 'bg-rose-50 border-rose-200',
    }
  }
  if (norm.includes('comment')) {
    return {
      icon: MessageSquare,
      color: 'text-slate-600',
      bg: 'bg-slate-100 border-slate-200',
    }
  }
  return {
    icon: FileText,
    color: 'text-blue-600',
    bg: 'bg-blue-50 border-blue-200',
  }
}

export const RecentActivityFeed: React.FC<RecentActivityFeedProps> = ({
  activity = [],
  onSelectActivityTarget,
}) => {
  return (
    <Card className="h-full border-border/80 flex flex-col justify-between">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-600" />
              <span>Recent Activity</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Live audit trail of editorial and governance actions
            </CardDescription>
          </div>
          <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Live sync
          </span>
        </div>
      </CardHeader>

      <CardContent className="pt-1 pb-4">
        {activity.length === 0 ? (
          <div className="py-10 text-center space-y-2">
            <div className="w-9 h-9 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Clock className="w-4 h-4" />
            </div>
            <p className="text-xs font-semibold text-slate-700">No Recent Governance Activity</p>
            <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
              Audit events, rule approvals, and managerial decisions will appear here in real-time as your team collaborates.
            </p>
          </div>
        ) : (
          <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {activity.map((item) => {
              const config = getActivityConfig(item.action)
              const Icon = config.icon

              return (
                <div
                  key={item.id}
                  onClick={() => item.reviewId && onSelectActivityTarget?.(item.reviewId)}
                  className={`relative group ${item.reviewId ? 'cursor-pointer' : ''}`}
                >
                  {/* Timeline node icon */}
                  <div
                    className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full border flex items-center justify-center shrink-0 shadow-2xs ${config.bg}`}
                  >
                    <Icon className={`w-3 h-3 ${config.color}`} />
                  </div>

                  <div className="rounded-md p-2 -my-1 transition-colors hover:bg-slate-50">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-900">
                        {item.action}
                      </span>
                      <span className="text-[10px] text-slate-400 shrink-0 font-mono">
                        {item.timestamp}
                      </span>
                    </div>

                    {item.details && (
                      <p className="text-xs text-slate-600 mt-0.5 leading-snug">
                        {item.details}
                      </p>
                    )}

                    <div className="flex items-center gap-2 mt-1.5">
                      <Avatar className="w-4 h-4">
                        <AvatarFallback className="text-[8px] bg-slate-200 text-slate-700">
                          {item.actorName.slice(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <span className="text-[11px] font-medium text-slate-700">
                        {item.actorName}
                      </span>
                      <span className="text-[10px] text-slate-400">•</span>
                      <span className="text-[10px] text-slate-400">{item.actorRole}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
