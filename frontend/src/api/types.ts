export interface Token {
  access_token: string
}

export interface User {
  id: number
  email: string
  created_at: string
}

export interface Product {
  id: number
  name: string
  website_url: string | null
  play_store_url: string | null
  category: string | null
  created_at: string
  updated_at: string
}

export interface ProductCreate {
  name: string
  website_url?: string | null
  play_store_url?: string | null
  category?: string | null
}

export interface DashboardProductSummary {
  product_id: number
  name: string
  category: string | null
  geo_score: number | null
  last_audit_date: string | null
  pipeline_status: string | null
  last_pipeline_date: string | null
  website_url: string | null
  play_store_url: string | null
}

export interface DashboardResponse {
  products: DashboardProductSummary[]
  total: number
}

export interface ScoreComponent {
  max_points: number
  earned: number
  details?: string
}

export interface ScoreBreakdown {
  total?: number
  documentation_depth?: ScoreComponent
  faq_presence?: ScoreComponent
  metadata_quality?: ScoreComponent
  structured_data?: ScoreComponent
  authority_signals?: ScoreComponent
  review_quality?: ScoreComponent
  freshness?: ScoreComponent
}

export interface ActionPlanStep {
  step: string
  component: string
  estimated_point_impact: number
}

export interface AuditReport {
  id: number
  product_id: number
  geo_score: number
  score_breakdown: ScoreBreakdown
  recommendations: { action_plan?: ActionPlanStep[] }
  created_at: string
}

export interface ReviewSummary {
  id: number
  product_id: number
  top_complaints: string[]
  top_feature_requests: string[]
  positive_themes: string[]
  negative_themes: string[]
  overall_sentiment_score: number | null
  reviews_analyzed_count: number
  batches_processed: number
  batches_failed: number
  status: string
  error_message: string | null
  created_at: string
  total_reviews: number
  average_rating: number | null
  rating_distribution: {
    one: number
    two: number
    three: number
    four: number
    five: number
  }
  sentiment_counts: {
    positive: number
    neutral: number
    negative: number
  }
}

export interface CompetitorScore {
  name?: string
  url?: string
  competitor_name?: string
  competitor_url?: string
  geo_score?: number
  score_breakdown?: ScoreBreakdown
  signals?: Record<string, unknown>
}

export interface CompareStatus {
  product_id: number
  status: string
  missing_features: string[]
  missing_faqs: string[]
  improvement_plan: string[]
  narrative_summary: string | null
  competitor_scores: CompetitorScore[]
  our_score: number | null
  our_breakdown: ScoreBreakdown | null
  our_product_name: string | null
  error_message: string | null
  created_at: string | null
}

export interface GeneratedContent {
  id: number
  product_id: number
  content_type: string
  content_body: string
  prompt_used: string | null
  created_at: string
}

export interface Report {
  id: number
  product_id: number
  file_path: string
  created_at: string
  html_content: string | null
}

export interface StageStatus {
  status: 'success' | 'partial' | 'failed' | 'skipped' | string
  duration_ms?: number
  error_message?: string | null
}

export interface PipelineRunStatus {
  id: number
  product_id: number
  started_at: string
  completed_at: string | null
  status: 'pending' | 'running' | 'success' | 'partial' | 'failed'
  stage_statuses: Record<string, StageStatus>
  competitor_urls: string[]
  error_message: string | null
}

export interface RunFullAuditAck {
  pipeline_run_id: number
  product_id: number
  status: string
  message: string
}

export interface CrawlStatus {
  product_id: number
  status: string
  title: string | null
  error_message: string | null
  last_crawled_at: string | null
}

export interface PlayStoreStatus {
  product_id: number
  status: string
  app_title: string | null
  error_message: string | null
  fetched_at: string | null
}

export interface ApiError {
  detail: string
}
