import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { mockRecentActivity } from '@/data/mockOverview'
import type { ActivityType } from '@/types/dashboard'
import {
  UploadCloud,
  CheckCircle2,
  Sparkles,
  GitPullRequest,
  CheckCheck,
  Clock,
} from 'lucide-react'

const activityIcons: Record<ActivityType, { icon: React.FC<{ className?: string }>; color: string; bg: string }> = {
  content_uploaded: {
    icon: UploadCloud,
    color: 'text-blue-600',
    bg: 'bg-blue-50 border-blue-200',
  },
  review_completed: {
    icon: Sparkles,
    color: 'text-purple-600',
    bg: 'bg-purple-50 border-purple-200',
  },
  correction_accepted: {
    icon: CheckCheck,
    color: 'text-emerald-600',
    bg: 'bg-emerald-50 border-emerald-200',
  },
  approval_requested: {
    icon: GitPullRequest,
    color: 'text-amber-600',
    bg: 'bg-amber-50 border-amber-200',
  },
  content_approved: {
    icon: CheckCircle2,
    color: 'text-emerald-700',
    bg: 'bg-emerald-100 border-emerald-300',
  },
}

interface RecentActivityFeedProps {
  onSelectActivityTarget?: (targetId: string) => void
}

export const RecentActivityFeed: React.FC<RecentActivityFeedProps> = ({
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
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          {mockRecentActivity.map((activity) => {
            const config = activityIcons[activity.type] || activityIcons.review_completed
            const Icon = config.icon

            return (
              <div
                key={activity.id}
                onClick={() => activity.targetId && onSelectActivityTarget?.(activity.targetId)}
                className="relative group cursor-pointer"
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
                      {activity.title}
                    </span>
                    <span className="text-[10px] text-slate-400 shrink-0 font-mono">
                      {activity.timestamp}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 mt-0.5 leading-snug">
                    {activity.description}
                  </p>

                  <div className="flex items-center gap-1.5 mt-1.5">
                    {activity.actor.avatar ? (
                      <Avatar className="w-4 h-4 rounded-full">
                        <AvatarImage src={activity.actor.avatar} alt={activity.actor.name} />
                        <AvatarFallback className="text-[8px]">
                          {activity.actor.name.substring(0, 2)}
                        </AvatarFallback>
                      </Avatar>
                    ) : (
                      <div className="w-4 h-4 rounded-full bg-blue-100 flex items-center justify-center text-[8px] font-bold text-blue-700">
                        AI
                      </div>
                    )}
                    <span className="text-[10px] text-slate-400">
                      {activity.actor.name} • {activity.actor.role}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
