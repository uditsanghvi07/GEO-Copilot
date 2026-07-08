import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiClientError, api } from '../api/client'

export function AddProductPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [playStoreUrl, setPlayStoreUrl] = useState('')
  const [category, setCategory] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      const product = await api.createProduct({
        name: name.trim(),
        website_url: websiteUrl.trim() || null,
        play_store_url: playStoreUrl.trim() || null,
        category: category.trim() || null,
      })

      const jobs: Promise<unknown>[] = []
      if (product.website_url) {
        jobs.push(api.triggerCrawl(product.id).catch(() => undefined))
      }
      if (product.play_store_url) {
        jobs.push(api.triggerPlayStoreAudit(product.id).catch(() => undefined))
      }
      await Promise.all(jobs)

      navigate(`/products/${product.id}?processing=1`)
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : 'Could not create product. Check your inputs and try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="font-heading text-2xl font-semibold text-text mb-2">
        Add product
      </h1>
      <p className="text-sm text-muted mb-8 font-body">
        Register a product to audit. Crawling starts immediately after you save.
      </p>

      <form
        onSubmit={handleSubmit}
        className="glass-card p-6 space-y-4"
      >
        <div>
          <label htmlFor="name" className="block text-sm text-muted mb-1.5 font-body">
            Product name
          </label>
          <input
            id="name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full glass-input px-3 py-2.5 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
          />
        </div>

        <div>
          <label htmlFor="website" className="block text-sm text-muted mb-1.5 font-body">
            Website URL
          </label>
          <input
            id="website"
            type="url"
            value={websiteUrl}
            onChange={(e) => setWebsiteUrl(e.target.value)}
            placeholder="https://"
            className="w-full glass-input px-3 py-2.5 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
          />
        </div>

        <div>
          <label htmlFor="playstore" className="block text-sm text-muted mb-1.5 font-body">
            Play Store URL (optional)
          </label>
          <input
            id="playstore"
            type="url"
            value={playStoreUrl}
            onChange={(e) => setPlayStoreUrl(e.target.value)}
            placeholder="https://play.google.com/store/apps/details?id=…"
            className="w-full glass-input px-3 py-2.5 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
          />
        </div>

        <div>
          <label htmlFor="category" className="block text-sm text-muted mb-1.5 font-body">
            Category (optional)
          </label>
          <input
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full glass-input px-3 py-2.5 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
          />
        </div>

        {error && (
          <p className="text-sm text-coral font-body" role="alert">
            {error}
          </p>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2.5 rounded-md bg-accent text-bg text-sm font-medium font-body hover:bg-accent/90 disabled:opacity-60 transition-colors"
          >
            {submitting ? 'Adding product…' : 'Add product'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-4 py-2.5 rounded-md hairline-border text-sm text-muted font-body hover:text-text transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
