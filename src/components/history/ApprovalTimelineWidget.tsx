import React from 'react'
import type { TimelineEvent } from '@/types/approval'
import {
  CheckCircle2,
  Clock,
  Circle,
  FileCheck2,
  Sparkles,
  GitPullRequest,
  UserCheck,
  Award,
} from 'lucide-react'

interface ApprovalTimelineWidgetProps {
  timeline: TimelineEvent[]
  className?: string
}

const isSystemEvent = (event: TimelineEvent) => {
  const role = (event.actorRole || '').toLowerCase()
  if (role.includes('sentinel') || role.includes('system') || role.includes('automated') || role.includes('governance')) {
    return true
  }
  const name = (event.actorName || '').toLowerCase()
  if (name.includes('sentinel') || name.includes('system') || name.includes('ai')) {
    return true
  }
  const note = (event.note || '').toLowerCase()
  if (note.includes('submitted for sign-off with') || note.includes('submission summary:') || note.includes('compliance scan completed')) {
    return true
  }
  return false
}

export const ApprovalTimelineWidget: React.FC<ApprovalTimelineWidgetProps> = ({
  timeline,
  className = '',
}) => {
  return (
    <div className={`space-y-3 ${className}`}>
      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
        {timeline.map((event, idx) => {
          const isCompleted = event.status === 'completed'
          const isCurrent = event.status === 'current'
          const isPending = event.status === 'pending'

          return (
            <div key={event.id || idx} className="relative group text-xs">
              {/* Timeline marker */}
              <div
                className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full flex items-center justify-center shrink-0 border shadow-2xs ${
                  isCompleted
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-600'
                    : isCurrent
                    ? 'bg-blue-600 border-blue-600 text-white ring-2 ring-blue-100 animate-pulse'
                    : 'bg-white border-slate-200 text-slate-300'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : isCurrent ? (
                  <Clock className="w-3 h-3 text-white" />
                ) : (
                  <Circle className="w-2.5 h-2.5 text-slate-300 fill-slate-100" />
                )}
              </div>

              <div className="rounded-md p-2 -my-1 transition-colors hover:bg-slate-50/80">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={`font-semibold ${
                        isCompleted
                          ? 'text-slate-900'
                          : isCurrent
                          ? 'text-blue-700'
                          : 'text-slate-400'
                      }`}
                    >
                      {event.stage}
                    </span>
                    {isSystemEvent(event) ? (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                        System Event
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        User Activity
                      </span>
                    )}
                  </div>

                  <span className="text-[10px] text-slate-400 font-mono">
                    {event.timestamp}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 mt-0.5 text-[11px] text-slate-500">
                  <span className="font-medium text-slate-700">{event.actorName}</span>
                  <span>•</span>
                  <span>{event.actorRole}</span>
                </div>

                {event.note && (
                  <p className="text-[11px] text-slate-600 mt-1 bg-slate-50 p-1.5 rounded border border-slate-100 italic">
                    "{event.note}"
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
