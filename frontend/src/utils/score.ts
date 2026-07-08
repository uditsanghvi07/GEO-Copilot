import type { ScoreBreakdown } from '../api/types'

export const BREAKDOWN_KEYS = [
  { key: 'documentation_depth', label: 'Documentation' },
  { key: 'faq_presence', label: 'FAQ' },
  { key: 'metadata_quality', label: 'Metadata' },
  { key: 'structured_data', label: 'Structured data' },
  { key: 'authority_signals', label: 'Authority' },
  { key: 'review_quality', label: 'Reviews' },
  { key: 'freshness', label: 'Freshness' },
] as const

export type BreakdownKey = (typeof BREAKDOWN_KEYS)[number]['key']

export const BREAKDOWN_MAX: Record<BreakdownKey, number> = {
  documentation_depth: 20,
  faq_presence: 15,
  metadata_quality: 10,
  structured_data: 20,
  authority_signals: 10,
  review_quality: 15,
  freshness: 10,
}

export function getBreakdownItems(breakdown?: ScoreBreakdown) {
  return BREAKDOWN_KEYS.map(({ key, label }) => {
    const component = breakdown?.[key]
    const earned = component?.earned ?? 0
    const max = component?.max_points ?? BREAKDOWN_MAX[key]
    return { key, label, earned, max }
  })
}
