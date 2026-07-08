import type {
  ApiError,
  AuditReport,
  CompareStatus,
  CrawlStatus,
  DashboardResponse,
  GeneratedContent,
  PipelineRunStatus,
  PlayStoreStatus,
  Product,
  ProductCreate,
  Report,
  ReviewSummary,
  RunFullAuditAck,
  Token,
  User,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

class ApiClientError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
  }
}

function getToken(): string | null {
  return localStorage.getItem('geo_token')
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem('geo_token', token)
  } else {
    localStorage.removeItem('geo_token')
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  expectJson = true,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  const token = getToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!expectJson) {
    if (!response.ok) {
      throw new ApiClientError('Request failed', response.status)
    }
    return undefined as T
  }

  if (response.status === 204) {
    return undefined as T
  }

  let payload: unknown = null
  const text = await response.text()
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { detail: text }
    }
  }

  if (!response.ok) {
    const detail =
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof (payload as ApiError).detail === 'string'
        ? (payload as ApiError).detail
        : `Request failed with status ${response.status}`
    throw new ApiClientError(detail, response.status)
  }

  return payload as T
}

export const api = {
  register: (email: string, password: string) =>
    request<Token>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<Token>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>('/auth/me'),

  getDashboard: () => request<DashboardResponse>('/dashboard'),

  listProducts: () => request<Product[]>('/products'),

  getProduct: (id: number) => request<Product>(`/products/${id}`),

  createProduct: (data: ProductCreate) =>
    request<Product>('/products', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateProduct: (id: number, data: Partial<ProductCreate>) =>
    request<Product>(`/products/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteProduct: (id: number) =>
    request<void>(`/products/${id}`, { method: 'DELETE' }, false),

  triggerCrawl: (productId: number) =>
    request<{ product_id: number; status: string; message: string }>('/crawl', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId }),
    }),

  getCrawlStatus: (productId: number) =>
    request<CrawlStatus>(`/crawl/status/${productId}`),

  triggerPlayStoreAudit: (productId: number) =>
    request<{ product_id: number; status: string; message: string }>(
      '/playstore-audit',
      {
        method: 'POST',
        body: JSON.stringify({ product_id: productId }),
      },
    ),

  getPlayStoreStatus: (productId: number) =>
    request<PlayStoreStatus>(`/playstore-audit/status/${productId}`),

  getLatestAudit: (productId: number) =>
    request<AuditReport>(`/audit/${productId}`),

  runAudit: (productId: number) =>
    request<AuditReport>('/audit', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId }),
    }),

  getReviewSummary: (productId: number) =>
    request<ReviewSummary>(`/reviews/summary/${productId}`),

  getCompareStatus: (productId: number) =>
    request<CompareStatus>(`/compare/status/${productId}`),

  triggerCompare: (productId: number, competitorUrls: string[]) =>
    request<{ product_id: number; status: string; message: string }>(
      '/compare',
      {
        method: 'POST',
        body: JSON.stringify({
          product_id: productId,
          competitor_urls: competitorUrls,
        }),
      },
    ),

  listContent: (productId: number) =>
    request<GeneratedContent[]>(`/content/${productId}`),

  generateFaq: (productId: number) =>
    request<GeneratedContent>('/generate-faq', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId }),
    }),

  generateBlog: (productId: number, topicHint?: string) =>
    request<GeneratedContent>('/generate-blog', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId, topic_hint: topicHint }),
    }),

  generateMeta: (productId: number) =>
    request<GeneratedContent>('/generate-meta', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId }),
    }),

  generateCampaign: (productId: number, campaignTheme?: string) =>
    request<GeneratedContent>('/generate-campaign', {
      method: 'POST',
      body: JSON.stringify({
        product_id: productId,
        campaign_theme: campaignTheme,
      }),
    }),

  runFullAudit: (productId: number, competitorUrls: string[] = []) =>
    request<RunFullAuditAck>('/run-full-audit', {
      method: 'POST',
      body: JSON.stringify({
        product_id: productId,
        competitor_urls: competitorUrls,
      }),
    }),

  getPipelineStatus: (pipelineRunId: number) =>
    request<PipelineRunStatus>(`/run-full-audit/status/${pipelineRunId}`),

  listReports: (productId: number) =>
    request<Report[]>(`/reports/${productId}`),

  deleteReport: (reportId: number) =>
    request<void>(`/reports/${reportId}`, { method: 'DELETE' }, false),

  getLatestReport: (productId: number) =>
    request<Report>(`/report/${productId}`),
}

export { ApiClientError }
