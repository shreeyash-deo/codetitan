/**
 * BrandShield Authentication Service
 * Connects to FastAPI OAuth2 / JWT authentication endpoints.
 *
 * Real FastAPI Endpoints:
 * - POST /api/v1/auth/register (Create account)
 * - POST /api/v1/auth/login    (Authenticate & receive JWT token)
 * - GET  /api/v1/auth/me       (Get authenticated user profile)
 * - POST /api/v1/auth/logout   (Session termination)
 */

import { apiClient } from './apiClient'
import type { UserProfile } from '@/types/user'

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  name: string
  email: string
  password: string
}

export interface AuthTokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserProfile
}

export const authService = {
  /**
   * Log in user and persist bearer token
   * FastAPI Route: POST /api/v1/auth/login
   */
  async login(credentials: LoginCredentials): Promise<AuthTokenResponse> {
    const tokenRes = await apiClient.post<{ access_token: string; token_type: string; expires_in: number }>(
      '/api/v1/auth/login',
      {
        email: credentials.email.trim(),
        password: credentials.password,
      }
    )

    if (tokenRes.access_token) {
      localStorage.setItem('brandshield_auth_token', tokenRes.access_token)
    }

    const userRes = await apiClient.get<any>('/api/v1/auth/me')
    const user: UserProfile = {
      id: String(userRes.id),
      name: userRes.name,
      email: userRes.email,
      role: userRes.role || 'User',
      status: 'online',
      pendingReviewsCount: 0,
    }

    return {
      ...tokenRes,
      user,
    }
  },

  /**
   * Register a new user and log them in
   * FastAPI Route: POST /api/v1/auth/register
   */
  async register(userData: RegisterData): Promise<UserProfile> {
    await apiClient.post<any>('/api/v1/auth/register', {
      name: userData.name.trim(),
      email: userData.email.trim(),
      password: userData.password,
    })

    const loginRes = await this.login({
      email: userData.email.trim(),
      password: userData.password,
    })

    return loginRes.user
  },

  /**
   * Get current authenticated user profile
   * FastAPI Route: GET /api/v1/auth/me
   */
  async getCurrentUser(): Promise<UserProfile | null> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('brandshield_auth_token') : null
    if (!token) {
      return null
    }

    try {
      const userRes = await apiClient.get<any>('/api/v1/auth/me')
      return {
        id: String(userRes.id),
        name: userRes.name,
        email: userRes.email,
        role: userRes.role || 'User',
        status: 'online',
        pendingReviewsCount: 0,
      }
    } catch {
      // Invalid or expired token: clear local state and return null
      localStorage.removeItem('brandshield_auth_token')
      return null
    }
  },

  /**
   * Terminate active session
   * FastAPI Route: POST /api/v1/auth/logout
   */
  async logout(): Promise<void> {
    localStorage.removeItem('brandshield_auth_token')
    localStorage.removeItem('brandshield_active_workspace_id')
    try {
      await apiClient.post('/api/v1/auth/logout')
    } catch {
      // Silently clear local session
    }
  },
}
