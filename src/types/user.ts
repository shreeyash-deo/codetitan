export interface UserProfile {
  id: string
  name: string
  email: string
  avatarUrl?: string
  role: 'Brand Lead' | 'Compliance Reviewer' | 'Content Creator' | 'Admin'
  status: 'online' | 'busy' | 'offline'
  pendingReviewsCount: number
}
