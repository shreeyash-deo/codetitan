import React from 'react'
import { Badge } from '@/components/ui/badge'
import type { ComplianceStatus } from '@/types/review'
import { CheckCircle2, AlertCircle, Clock, XCircle } from 'lucide-react'

interface StatusBadgeProps {
  status: ComplianceStatus
  showIcon?: boolean
  className?: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  showIcon = true,
  className,
}) => {
  switch (status) {
    case 'approved':
      return (
        <Badge variant="success" className={className}>
          {showIcon && <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />}
          Approved
        </Badge>
      )
    case 'in_review':
      return (
        <Badge variant="blue" className={className}>
          {showIcon && <Clock className="w-3 h-3 mr-1 text-blue-600 animate-pulse" />}
          In Review
        </Badge>
      )
    case 'flagged':
      return (
        <Badge variant="warning" className={className}>
          {showIcon && <AlertCircle className="w-3 h-3 mr-1 text-amber-600" />}
          Flagged
        </Badge>
      )
    case 'rejected':
      return (
        <Badge variant="destructive" className={className}>
          {showIcon && <XCircle className="w-3 h-3 mr-1 text-rose-600" />}
          Rejected
        </Badge>
      )
    default:
      return null
  }
}
