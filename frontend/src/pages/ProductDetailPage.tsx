import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ExternalLink, Play, Trash2 } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { ApiClientError, api } from '../api/client'
import type {
  AuditReport,
  CompareStatus,
  GeneratedContent,
  PipelineRunStatus,
  Product,
  Report,
  ReviewSummary,
} from '../api/types'
import { ActionPlanChecklist } from '../components/ActionPlanChecklist'
import { AuditLoadingOverlay } from '../components/AuditLoadingOverlay'
import { CompetitorTable } from '../components/CompetitorTable'
import {
  ContentGeneratorPanel,
} from '../components/ContentGeneratorPanel'
import { GeoScoreRing } from '../components/GeoScoreRing'
import { JobStatus } from '../components/JobStatus'
import { SentimentChart } from '../components/SentimentChart'
import { TabBar } from '../components/TabBar'
import { useIngestionStatus } from '../hooks/useIngestionStatus'
import { usePolling } from '../hooks/usePolling'
import { formatDateTime } from '../utils/format'
import { getCompetitorDisplayName } from '../utils/displayNames'
import { isPipelineFinished } from '../utils/pipelineProgress'

function hasUsableReviewSummary(summary: ReviewSummary | null): boolean {
  if (!summary) return false
  if (summary.reviews_analyzed_count > 0) return true
  if (summary.status === 'success' || summary.status === 'partial') return true
  return false
}

type TabId = 'overview' | 'reviews' | 'competitors' | 'content' | 'reports'
type ContentType = 'faq' | 'blog' | 'meta' | 'campaign'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'reviews', label: 'Reviews' },
  { id: 'competitors', label: 'Competitors' },
  { id: 'content', label: 'Content generator' },
  { id: 'reports', label: 'Reports' },
] as const

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const productId = Number(id)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [product, setProduct] = useState<Product | null>(null)
  const [audit, setAudit] = useState<AuditReport | null>(null)
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null)
  const [comparison, setComparison] = useState<CompareStatus | null>(null)
  const [reports, setReports] = useState<Report[]>([])
  const [contentList, setContentList] = useState<GeneratedContent[]>([])
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [pipelineRunId, setPipelineRunId] = useState<number | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineRunStatus | null>(
    null,
  )
  const [auditRunning, setAuditRunning] = useState(false)
  const [processing, setProcessing] = useState(
    searchParams.get('processing') === '1',
  )

  const [panelOpen, setPanelOpen] = useState(false)
  const [panelType, setPanelType] = useState<ContentType | null>(null)
  const [panelLoading, setPanelLoading] = useState(false)
  const [panelResult, setPanelResult] = useState<GeneratedContent | null>(null)
  const [panelError, setPanelError] = useState<string | null>(null)

  const [viewingReport, setViewingReport] = useState<Report | null>(null)
  const [competitorUrls, setCompetitorUrls] = useState('')
  const [playStoreUrl, setPlayStoreUrl] = useState('')
  const [savingPlayStore, setSavingPlayStore] = useState(false)
  const [playStoreSaved, setPlayStoreSaved] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deletingReportId, setDeletingReportId] = useState<number | null>(null)

  const ingestionStages = useIngestionStatus(
    productId,
    processing && !pipelineRunId,
  )

  const displayStages = pipelineStatus?.stage_statuses ?? ingestionStages

  useEffect(() => {
    if (!processing || pipelineRunId) return
    const stages = Object.values(ingestionStages)
    if (
      stages.length > 0 &&
      stages.every(
        (s) =>
          s.status === 'success' || s.status === 'failed' || s.status === 'skipped',
      )
    ) {
      setProcessing(false)
      searchParams.delete('processing')
      setSearchParams(searchParams, { replace: true })
    }
  }, [ingestionStages, processing, pipelineRunId, searchParams, setSearchParams])

  useEffect(() => {
    if (product?.play_store_url) {
      setPlayStoreUrl(product.play_store_url)
    }
  }, [product?.play_store_url])

  const loadCore = useCallback(async () => {
    if (!productId || Number.isNaN(productId)) return
    const p = await api.getProduct(productId)
    setProduct(p)

    try {
      const auditData = await api.getLatestAudit(productId)
      setAudit(auditData)
    } catch (err) {
      if (!(err instanceof ApiClientError && err.status === 404)) throw err
      setAudit(null)
    }
  }, [productId])

  const loadTabData = useCallback(
    async (tab: TabId) => {
      if (!productId || Number.isNaN(productId)) return

      if (tab === 'reviews') {
        try {
          const data = await api.getReviewSummary(productId)
          setReviewSummary(data)
        } catch (err) {
          if (err instanceof ApiClientError && (err.status === 404 || err.status === 202)) {
            setReviewSummary(null)
          }
        }
      }

      if (tab === 'competitors') {
        try {
          const data = await api.getCompareStatus(productId)
          setComparison(data)
        } catch (err) {
          if (err instanceof ApiClientError && (err.status === 404 || err.status === 202)) {
            setComparison(null)
          }
        }
      }

      if (tab === 'content') {
        const data = await api.listContent(productId)
        setContentList(data)
      }

      if (tab === 'reports') {
        try {
          const data = await api.listReports(productId)
          setReports(data)
        } catch {
          setReports([])
        }
      }
    },
    [productId],
  )

  useEffect(() => {
    if (!productId || Number.isNaN(productId)) {
      navigate('/')
      return
    }

    setLoading(true)
    loadCore()
      .catch(() =>
        setError('Could not load product details. Refresh the page to try again.'),
      )
      .finally(() => setLoading(false))
  }, [productId, loadCore, navigate])

  useEffect(() => {
    loadTabData(activeTab)
  }, [activeTab, loadTabData])

  const pollPipeline = useCallback(async () => {
    if (!pipelineRunId) throw new Error('No pipeline')
    return api.getPipelineStatus(pipelineRunId)
  }, [pipelineRunId])

  usePolling(
    pollPipeline,
    3000,
    Boolean(pipelineRunId),
    (data) => {
      setPipelineStatus(data)
      if (data.status === 'success' || data.status === 'partial' || data.status === 'failed') {
        setAuditRunning(false)
        setProcessing(false)
        setPipelineRunId(null)
        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev)
            next.delete('processing')
            return next
          },
          { replace: true },
        )
        void loadCore().catch(() =>
          setError('Audit finished but results could not be refreshed. Reload the page.'),
        )
        void Promise.all([
          loadTabData('reviews'),
          loadTabData('competitors'),
          loadTabData('content'),
          loadTabData('reports'),
        ])
      }
    },
    (data) =>
      data.status === 'success' ||
      data.status === 'partial' ||
      data.status === 'failed',
  )

  const handleDeleteReport = async (report: Report) => {
    const confirmed = window.confirm(
      `Delete the audit report from ${formatDateTime(report.created_at)}? This cannot be undone.`,
    )
    if (!confirmed) return

    setDeletingReportId(report.id)
    setError(null)
    try {
      await api.deleteReport(report.id)
      setReports((prev) => prev.filter((r) => r.id !== report.id))
      if (viewingReport?.id === report.id) {
        setViewingReport(null)
      }
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : 'Could not delete report. Try again in a moment.',
      )
    } finally {
      setDeletingReportId(null)
    }
  }

  const handleDeleteProduct = async () => {
    if (!product) return
    const confirmed = window.confirm(
      `Delete "${product.name}"? This removes all audits, reports, and generated content for this product.`,
    )
    if (!confirmed) return

    setDeleting(true)
    setError(null)
    try {
      await api.deleteProduct(product.id)
      navigate('/')
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : 'Could not delete product. Try again in a moment.',
      )
      setDeleting(false)
    }
  }

  const handleSavePlayStoreUrl = async () => {
    if (!product) return
    setSavingPlayStore(true)
    setPlayStoreSaved(false)
    setError(null)
    try {
      const updated = await api.updateProduct(product.id, {
        play_store_url: playStoreUrl.trim() || null,
      })
      setProduct(updated)
      setPlayStoreSaved(true)
      setTimeout(() => setPlayStoreSaved(false), 2500)
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : 'Could not save Play Store URL. Check the link and try again.',
      )
    } finally {
      setSavingPlayStore(false)
    }
  }

  const handleRunFullAudit = async () => {
    if (!product) return
    setAuditRunning(true)
    setError(null)
    try {
      const urls = competitorUrls
        .split('\n')
        .map((u) => u.trim())
        .filter(Boolean)
      const ack = await api.runFullAudit(product.id, urls)
      setPipelineRunId(ack.pipeline_run_id)
      setPipelineStatus(null)
      setProcessing(true)
    } catch (err) {
      setAuditRunning(false)
      setError(
        err instanceof ApiClientError
          ? err.message
          : 'Could not start full audit. Try again in a moment.',
      )
    }
  }

  const openContentPanel = (type: ContentType) => {
    setPanelType(type)
    setPanelOpen(true)
    setPanelResult(null)
    setPanelError(null)
  }

  const handleGenerate = async (instructions: string) => {
    if (!product || !panelType) return
    setPanelLoading(true)
    setPanelError(null)
    try {
      let result: GeneratedContent
      switch (panelType) {
        case 'faq':
          result = await api.generateFaq(product.id)
          break
        case 'blog':
          result = await api.generateBlog(product.id, instructions || undefined)
          break
        case 'meta':
          result = await api.generateMeta(product.id)
          break
        case 'campaign':
          result = await api.generateCampaign(product.id, instructions || undefined)
          break
      }
      setPanelResult(result)
      const list = await api.listContent(product.id)
      setContentList(list)
    } catch (err) {
      setPanelError(
        err instanceof ApiClientError
          ? err.message
          : 'Content generation failed. Ensure crawling has completed and try again.',
      )
    } finally {
      setPanelLoading(false)
    }
  }

  const competitorDisplayNames = useMemo(
    () =>
      (comparison?.competitor_scores ?? []).map((comp, i) =>
        getCompetitorDisplayName(comp, i),
      ),
    [comparison?.competitor_scores],
  )

  const actionPlan = useMemo(() => {
    const plan = audit?.recommendations?.action_plan
    return Array.isArray(plan) ? plan : []
  }, [audit])

  const pipelineFinished = isPipelineFinished(
    pipelineStatus?.status,
    displayStages,
  )

  const showAuditOverlay =
    auditRunning || (processing && Boolean(pipelineRunId) && !pipelineFinished)

  if (loading) {
    return <p className="text-sm text-muted font-body">Loading product…</p>
  }

  if (!product) {
    return (
      <p className="text-sm text-coral font-body" role="alert">
        Product not found.
      </p>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
        <div className="min-w-0">
          <Link
            to="/"
            className="text-xs text-muted hover:text-accent font-body mb-3 inline-block"
          >
            ← Back to dashboard
          </Link>
          <h1 className="font-heading text-2xl font-semibold text-text">
            {product.name}
          </h1>
          <div className="flex flex-wrap gap-4 mt-3 text-sm">
            {product.website_url && (
              <a
                href={product.website_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-muted hover:text-accent font-body"
              >
                Website <ExternalLink size={12} />
              </a>
            )}
            {product.play_store_url && (
              <a
                href={product.play_store_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-muted hover:text-accent font-body"
              >
                Play Store <ExternalLink size={12} />
              </a>
            )}
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-6">
          <GeoScoreRing
            score={audit?.geo_score ?? null}
            breakdown={audit?.score_breakdown}
            size="lg"
            showLegend={false}
          />
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            type="button"
            onClick={handleDeleteProduct}
            disabled={deleting || auditRunning}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md hairline-border text-sm text-coral font-body hover:border-coral/40 disabled:opacity-60 transition-colors"
          >
            <Trash2 size={14} />
            {deleting ? 'Deleting…' : 'Delete product'}
          </button>
          <button
            type="button"
            onClick={handleRunFullAudit}
            disabled={auditRunning}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-accent text-bg text-sm font-medium font-body hover:bg-accent/90 disabled:opacity-60 transition-colors whitespace-nowrap"
          >
            <Play size={14} />
            {auditRunning ? 'Audit running…' : 'Run full audit'}
          </button>
        </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
        <div>
          <label htmlFor="play-store-url" className="block text-sm text-muted mb-1.5 font-body">
            Play Store URL — {product.name}
          </label>
          <p className="text-xs text-muted mb-2 font-body">
            Required to analyze your app listing and Play Store reviews. This is separate from competitor URLs below.
          </p>
          <div className="flex gap-2">
            <input
              id="play-store-url"
              type="url"
              value={playStoreUrl}
              onChange={(e) => setPlayStoreUrl(e.target.value)}
              placeholder="https://play.google.com/store/apps/details?id=..."
              className="flex-1 glass-input px-3 py-2 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30 font-body"
            />
            <button
              type="button"
              onClick={handleSavePlayStoreUrl}
              disabled={savingPlayStore}
              className="px-3 py-2 rounded-md hairline-border text-sm text-text font-body hover:border-accent/40 disabled:opacity-60 whitespace-nowrap"
            >
              {savingPlayStore ? 'Saving…' : playStoreSaved ? 'Saved' : 'Save'}
            </button>
          </div>
          {playStoreUrl.includes('/search') && (
            <p className="text-xs text-coral mt-2 font-body">
              This looks like a search link. Open the specific app and copy its
              URL — it should contain <span className="font-mono-num">/apps/details?id=</span>.
            </p>
          )}
        </div>

        <div>
          <label htmlFor="competitors" className="block text-sm text-muted mb-1.5 font-body">
            Competitor URLs (one per line, optional)
          </label>
          <p className="text-xs text-muted mb-2 font-body">
            Websites or Play Store links for competitor comparison only. Does not analyze your own listing.
          </p>
          <textarea
            id="competitors"
            rows={3}
            value={competitorUrls}
            onChange={(e) => setCompetitorUrls(e.target.value)}
            placeholder="https://competitor.com"
            className="w-full glass-input px-3 py-2 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30 resize-none font-body"
          />
        </div>
      </div>

      {error && (
        <p className="text-sm text-coral font-body" role="alert">
          {error}
        </p>
      )}

      <AuditLoadingOverlay
        open={showAuditOverlay}
        productName={product.name}
        competitorNames={competitorDisplayNames}
        stageStatuses={displayStages}
        overallStatus={pipelineStatus?.status ?? (processing ? 'running' : undefined)}
      />

      {!showAuditOverlay &&
        (processing ||
          pipelineStatus ||
          Object.keys(displayStages).length > 0) && (
        <JobStatus
          stageStatuses={displayStages}
          overallStatus={pipelineStatus?.status ?? (processing ? 'running' : undefined)}
          productName={product.name}
          competitorNames={competitorDisplayNames}
        />
      )}

      <div>
        <TabBar
          tabs={TABS.map((t) => ({ id: t.id, label: t.label }))}
          activeTab={activeTab}
          onChange={(id) => setActiveTab(id as TabId)}
        />

        <div className="pt-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === 'overview' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="glass-card p-5">
                    <h3 className="font-heading text-base font-semibold mb-4">
                      Score breakdown — {product.name}
                    </h3>
                    <GeoScoreRing
                      score={audit?.geo_score ?? null}
                      breakdown={audit?.score_breakdown}
                      size="lg"
                      showLegend
                    />
                  </div>
                  <div className="glass-card p-5">
                    <h3 className="font-heading text-base font-semibold mb-4">
                      Action plan — {product.name}
                    </h3>
                    <ActionPlanChecklist steps={actionPlan} />
                  </div>
                </div>
              )}

              {activeTab === 'reviews' && (
                <div className="space-y-6">
                  {hasUsableReviewSummary(reviewSummary) ? (
                    <>
                      <SentimentChart
                        summary={reviewSummary}
                        productName={product.name}
                      />
                      {(reviewSummary.positive_themes.length > 0 ||
                        reviewSummary.negative_themes.length > 0) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <ThemeList
                            title="What people like"
                            tone="positive"
                            items={reviewSummary.positive_themes}
                          />
                          <ThemeList
                            title="What frustrates people"
                            tone="negative"
                            items={reviewSummary.negative_themes}
                          />
                        </div>
                      )}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <RankedList
                          title="Top complaints"
                          items={reviewSummary.top_complaints}
                        />
                        <RankedList
                          title="Top feature requests"
                          items={reviewSummary.top_feature_requests}
                        />
                      </div>
                    </>
                  ) : (
                    <EmptyTabMessage
                      message={
                        product.play_store_url
                          ? 'No review analysis yet. Run a full audit to analyze Play Store reviews.'
                          : 'No Play Store URL configured for this product. Add a Play Store link to enable review analysis.'
                      }
                    />
                  )}
                </div>
              )}

              {activeTab === 'competitors' && (
                <div className="glass-card p-5">
                  <CompetitorTable
                    comparison={
                      comparison ?? {
                        product_id: product.id,
                        status: 'pending',
                        missing_features: [],
                        missing_faqs: [],
                        improvement_plan: [],
                        narrative_summary: null,
                        competitor_scores: [],
                        our_score: null,
                        our_breakdown: null,
                        our_product_name: product.name,
                        error_message: null,
                        created_at: null,
                      }
                    }
                    productName={product.name}
                    ourBreakdown={audit?.score_breakdown}
                  />
                </div>
              )}

              {activeTab === 'content' && (
                <div className="space-y-6">
                  <p className="text-sm text-muted font-body">
                    Generate AI-optimized content grounded in{' '}
                    <span className="text-text font-medium">{product.name}</span> data.
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {(
                      [
                        ['faq', 'Generate FAQ'],
                        ['blog', 'Generate blog post'],
                        ['meta', 'Generate meta description'],
                        ['campaign', 'Generate campaign bundle'],
                      ] as const
                    ).map(([type, label]) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => openContentPanel(type)}
                        className="px-4 py-2 rounded-md hairline-border text-sm text-text font-body hover:border-accent/40 transition-colors"
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {contentList.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="font-heading text-sm font-semibold text-muted">
                        Previously generated for {product.name}
                      </h3>
                      {contentList.map((item) => (
                        <div
                          key={item.id}
                          className="glass-card p-4"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-mono-num text-muted uppercase">
                              {item.content_type}
                            </span>
                            <span className="text-xs font-mono-num text-muted">
                              {formatDateTime(item.created_at)}
                            </span>
                          </div>
                          <p className="text-sm text-text font-body line-clamp-3">
                            {item.content_body}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'reports' && (
                <div className="space-y-3">
                  {reports.length === 0 ? (
                    <EmptyTabMessage message="No reports generated yet. Run a full audit to build an HTML report." />
                  ) : (
                    reports.map((report) => (
                      <div
                        key={report.id}
                        className="glass-card p-4 flex items-center justify-between gap-4"
                      >
                        <div>
                          <p className="text-sm text-text font-body">
                            Audit report — {product.name}
                          </p>
                          <p className="text-xs text-muted font-mono-num mt-0.5">
                            {formatDateTime(report.created_at)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setViewingReport(report)}
                            className="px-3 py-1.5 rounded-md hairline-border text-sm text-accent font-body hover:border-accent/40"
                          >
                            View
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteReport(report)}
                            disabled={deletingReportId === report.id}
                            aria-label="Delete report"
                            className="p-1.5 rounded-md text-muted hover:text-coral hover:bg-coral-muted disabled:opacity-50 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <ContentGeneratorPanel
        open={panelOpen}
        contentType={panelType}
        productName={product.name}
        loading={panelLoading}
        result={panelResult}
        error={panelError}
        onClose={() => setPanelOpen(false)}
        onGenerate={handleGenerate}
      />

      <AnimatePresence>
        {viewingReport?.html_content && (
          <>
            <motion.button
              type="button"
              aria-label="Close report"
              className="fixed inset-0 bg-bg/80 z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setViewingReport(null)}
            />
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Audit report"
              className="fixed inset-4 md:inset-8 z-50 glass-panel-strong overflow-hidden flex flex-col"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-sm font-mono-num text-muted">
                  {product.name} · {formatDateTime(viewingReport.created_at)}
                </span>
                <button
                  type="button"
                  onClick={() => setViewingReport(null)}
                  className="text-sm text-muted hover:text-text font-body"
                >
                  Close
                </button>
              </div>
              <iframe
                title="Audit report"
                srcDoc={viewingReport.html_content}
                className="flex-1 w-full bg-white"
                sandbox="allow-same-origin"
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

function RankedList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="glass-card p-5">
      <h3 className="font-heading text-base font-semibold mb-4">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted font-body">No items recorded.</p>
      ) : (
        <ol className="space-y-2">
          {items.map((item, index) => (
            <li
              key={`${item}-${index}`}
              className="flex items-start gap-3 text-sm font-body"
            >
              <span className="font-mono-num text-muted shrink-0 w-5">
                {index + 1}
              </span>
              <span className="text-text">{item}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function ThemeList({
  title,
  tone,
  items,
}: {
  title: string
  tone: 'positive' | 'negative'
  items: string[]
}) {
  const dotColor = tone === 'positive' ? 'var(--color-accent)' : 'var(--color-coral)'
  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: dotColor }}
        />
        <h3 className="font-heading text-base font-semibold">{title}</h3>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-muted font-body">No themes recorded.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li
              key={`${item}-${index}`}
              className="flex items-start gap-2.5 text-sm font-body text-text"
            >
              <span
                className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: dotColor }}
              />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function EmptyTabMessage({ message }: { message: string }) {
  return (
    <div className="glass-card p-8 text-center">
      <p className="text-sm text-muted font-body">{message}</p>
    </div>
  )
}
