import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Plus, Trash2 } from 'lucide-react'
import { ApiClientError, api } from '../api/client'
import type { DashboardProductSummary } from '../api/types'
import { GeoScoreRing } from '../components/GeoScoreRing'
import { SkeletonCard } from '../components/SkeletonCard'
import { StatusPill } from '../components/StatusPill'
import { formatDate, healthFromScore } from '../utils/format'

export function DashboardPage() {
  const [products, setProducts] = useState<DashboardProductSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const loadDashboard = () => {
    setLoading(true)
    api
      .getDashboard()
      .then((data) => setProducts(data.products))
      .catch(() =>
        setError('Could not load dashboard data. Refresh the page to try again.'),
      )
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  const handleDelete = async (productId: number, productName: string) => {
    const confirmed = window.confirm(
      `Delete "${productName}"? This removes all audits, reports, and generated content for this product.`,
    )
    if (!confirmed) return

    setDeletingId(productId)
    setError(null)
    try {
      await api.deleteProduct(productId)
      setProducts((prev) => prev.filter((p) => p.product_id !== productId))
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : 'Could not delete product. Try again in a moment.',
      )
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-text">
            Products
          </h1>
          <p className="text-sm text-muted mt-1 font-body">
            Monitor GEO discoverability across your product portfolio
          </p>
        </div>
        <Link
          to="/products/new"
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-accent text-bg text-sm font-medium font-body hover:bg-accent/90 transition-colors"
        >
          <Plus size={16} />
          Add product
        </Link>
      </div>

      {error && (
        <p className="text-sm text-coral mb-6 font-body" role="alert">
          {error}
        </p>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && products.length === 0 && (
        <div className="glass-card p-12 text-center max-w-lg mx-auto">
          <h2 className="font-heading text-lg font-semibold text-text mb-2">
            No products tracked yet
          </h2>
          <p className="text-sm text-muted font-body mb-6 leading-relaxed">
            Add your first product to start measuring how discoverable it is
            across AI systems. We will crawl the website, analyze the Play Store
            listing, and compute a GEO score.
          </p>
          <Link
            to="/products/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-accent text-bg text-sm font-medium font-body hover:bg-accent/90 transition-colors"
          >
            <Plus size={16} />
            Add your first product
          </Link>
        </div>
      )}

      {!loading && products.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map((product, index) => {
            const health = healthFromScore(product.geo_score)
            return (
              <motion.div
                key={product.product_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.06, duration: 0.35 }}
                className="relative glass-card hover:border-accent/30 transition-colors group"
              >
                <Link
                  to={`/products/${product.product_id}`}
                  className="block p-5 pb-12 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent/40 rounded-lg"
                >
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="min-w-0">
                      <h2 className="font-heading text-base font-semibold text-text truncate">
                        {product.name}
                      </h2>
                      {product.category && (
                        <p className="text-xs text-muted mt-0.5 font-body">
                          {product.category}
                        </p>
                      )}
                    </div>
                    <StatusPill tone={health.tone} label={health.label} />
                  </div>

                  <div className="flex justify-center mb-4">
                    <GeoScoreRing score={product.geo_score} size="sm" />
                  </div>

                  <p className="text-xs text-muted text-center font-body">
                    Last audit{' '}
                    <span className="font-mono-num text-text">
                      {formatDate(product.last_audit_date)}
                    </span>
                  </p>
                </Link>
                <button
                  type="button"
                  onClick={() => handleDelete(product.product_id, product.name)}
                  disabled={deletingId === product.product_id}
                  aria-label={`Delete ${product.name}`}
                  className="absolute bottom-3 right-3 z-10 p-1.5 rounded-md text-muted hover:text-coral hover:bg-coral-muted opacity-70 group-hover:opacity-100 focus:opacity-100 focus-visible:ring-1 focus-visible:ring-coral/40 transition-all disabled:opacity-50"
                >
                  <Trash2 size={14} />
                </button>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
