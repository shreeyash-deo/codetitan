export interface UserProfile {
  id: string
  name: string
  email: string
  avatarUrl?: string
  role: string
  status: 'online' | 'busy' | 'offline'
  pendingReviewsCount: number
}
