/**
 * BrandShield Central API Client
 * Configured for FastAPI backend integration with automatic fallback to mock mode.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true'

export class ApiClientError extends Error {
  statusCode: number
  detail?: string

  constructor(message: string, statusCode: number, detail?: string) {
    super(message)
    this.name = 'ApiClientError'
    this.statusCode = statusCode
    this.detail = detail
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>
}

class ApiClient {
  public baseUrl: string
  private defaultHeaders: Record<string, string>

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/+$/, '')
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    }
  }

  public isMockMode(): boolean {
    return USE_MOCK_DATA
  }

  private getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('brandshield_auth_token')
    }
    return null
  }

  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    const url = new URL(`${this.baseUrl}${cleanEndpoint}`)

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value))
        }
      })
    }

    return url.toString()
  }

  public async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { params, headers, ...customConfig } = options

    const token = this.getAuthToken()
    const isFormData = customConfig.body instanceof FormData
    const requestHeaders: Record<string, string> = {
      ...(isFormData ? {} : this.defaultHeaders),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers as Record<string, string>),
    }

    const config: RequestInit = {
      ...customConfig,
      headers: requestHeaders,
    }

    const url = this.buildUrl(endpoint, params)

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        let errorDetail: string | undefined
        try {
          const errorJson = await response.json()
          errorDetail = errorJson.detail || errorJson.message
        } catch {
          errorDetail = response.statusText
        }

        throw new ApiClientError(
          `API request failed with status ${response.status}`,
          response.status,
          errorDetail
        )
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T
      }

      return (await response.json()) as T
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error
      }
      throw new ApiClientError(
        error instanceof Error ? error.message : 'Network error communicating with FastAPI backend',
        0
      )
    }
  }

  public get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' })
  }

  public post<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  public put<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  public patch<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  public delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' })
  }

  public upload<T>(endpoint: string, formData: FormData, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: formData,
    })
  }
}

export const apiClient = new ApiClient(API_BASE_URL)
