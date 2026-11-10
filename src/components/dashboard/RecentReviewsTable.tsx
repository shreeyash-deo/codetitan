import React, { useState } from 'react'
import type { ReviewItem } from '@/types/review'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  FileCheck2,
  ArrowRight,
  Filter,
  Search,
  Inbox,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'

interface RecentReviewsTableProps {
  reviews: ReviewItem[]
  onSelectReview: (review: ReviewItem) => void
  onOpenSubmitModal?: () => void
}

export const RecentReviewsTable: React.FC<RecentReviewsTableProps> = ({
  reviews,
  onSelectReview,
  onOpenSubmitModal,
}) => {
  const [filterChannel, setFilterChannel] = useState<string>('all')

  const filteredReviews = reviews.filter((r) => {
    if (filterChannel === 'all') return true
    return r.channel.toLowerCase() === filterChannel.toLowerCase()
  })

  return (
    <Card className="border-border/80 shadow-xs">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-blue-600" />
                <span>Recent Reviews</span>
              </CardTitle>
              <Badge variant="neutral" className="text-[10px]">
                {reviews.length} assets
              </Badge>
            </div>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Select any row to inspect issues, flagged phrases, and apply AI suggestions
            </CardDescription>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {/* Channel filter pills */}
            <select
              value={filterChannel}
              onChange={(e) => setFilterChannel(e.target.value)}
              className="h-8 rounded-md border border-input bg-white px-2 py-1 text-xs text-slate-700 shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="all">All Content Types</option>
              <option value="blog">Blog Posts</option>
              <option value="ad creative">Ad Creatives</option>
              <option value="product landing">Landing Pages</option>
              <option value="email campaign">Email Campaigns</option>
              <option value="press release">Press Releases</option>
              <option value="social">Social Media</option>
            </select>

            <Link
              to="/content-review"
              className="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1 ml-1"
            >
              <span>Full Studio</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {filteredReviews.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Inbox className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">No content matches filter</p>
              <p className="text-xs text-slate-500 mt-0.5">Adjust filter options or submit a new asset for automated review.</p>
            </div>
            {onOpenSubmitModal && (
              <Button
                variant="primaryBlue"
                size="sm"
                onClick={onOpenSubmitModal}
                className="mt-2 text-xs gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Submit Asset for Review</span>
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50/70 border-b border-border/80 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 sm:px-5 py-3">Content Name</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Submitted By</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredReviews.map((rev) => (
                  <tr
                    key={rev.id}
                    onClick={() => onSelectReview(rev)}
                    className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                  >
                    {/* Content name & preview */}
                    <td className="px-4 sm:px-5 py-3.5 max-w-xs">
                      <div className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors truncate">
                        {rev.title}
                      </div>
                      <div className="text-[11px] text-slate-400 truncate mt-0.5">
                        {rev.summary}
                      </div>
                    </td>

                    {/* Content type */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <Badge variant="outline" className="text-[10px] font-normal">
                        {rev.contentType}
                      </Badge>
                    </td>

                    {/* Submitted by */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Avatar className="w-5 h-5 shrink-0">
                          <AvatarImage src={rev.author.avatar} alt={rev.author.name} />
                          <AvatarFallback className="text-[9px]">
                            {rev.author.name.substring(0, 2)}
                          </AvatarFallback>
                        </Avatar>
                        <span className="text-slate-700 font-medium truncate">
                          {rev.author.name}
                        </span>
                      </div>
                    </td>

                    {/* Compliance score */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`font-bold ${
                            rev.score >= 90
                              ? 'text-emerald-700'
                              : rev.score >= 75
                              ? 'text-blue-700'
                              : 'text-amber-700'
                          }`}
                        >
                          {rev.score}
                        </span>
                        <span className="text-slate-400 text-[10px]">/100</span>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <StatusBadge status={rev.status} />
                    </td>

                    {/* Date */}
                    <td className="px-4 py-3.5 whitespace-nowrap text-slate-500 text-[11px]">
                      {rev.date}
                    </td>

                    {/* Action */}
                    <td className="px-4 py-3.5 whitespace-nowrap text-right">
                      <span className="text-blue-600 font-medium text-xs group-hover:underline inline-flex items-center gap-1">
                        Inspect
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
