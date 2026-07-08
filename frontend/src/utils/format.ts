/** India Standard Time — all API datetimes are stored as UTC in the backend. */
export const IST_TIMEZONE = 'Asia/Kolkata'

/**
 * Parse API datetime strings. Backend sends naive UTC ISO strings without a
 * `Z` suffix — treat those as UTC before converting to IST for display.
 */
export function parseApiDate(value: string): Date | null {
  const trimmed = value.trim()
  if (!trimmed) return null

  const hasTimezone = /[zZ]$|[+-]\d{2}:\d{2}$/.test(trimmed)
  const normalized = hasTimezone ? trimmed : `${trimmed}Z`
  const date = new Date(normalized)

  if (Number.isNaN(date.getTime())) return null
  return date
}

const istDateOptions: Intl.DateTimeFormatOptions = {
  timeZone: IST_TIMEZONE,
  year: 'numeric',
  month: 'short',
  day: 'numeric',
}

const istDateTimeOptions: Intl.DateTimeFormatOptions = {
  ...istDateOptions,
  hour: '2-digit',
  minute: '2-digit',
  hour12: true,
  timeZoneName: 'short',
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = parseApiDate(value)
  if (!date) return '—'
  return date.toLocaleString('en-IN', istDateOptions)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = parseApiDate(value)
  if (!date) return '—'
  return date.toLocaleString('en-IN', istDateTimeOptions)
}

export function healthFromScore(score: number | null | undefined): {
  label: 'Healthy' | 'Needs attention' | 'Critical' | 'Unscored'
  tone: 'healthy' | 'attention' | 'critical' | 'muted'
} {
  if (score == null) {
    return { label: 'Unscored', tone: 'muted' }
  }
  if (score >= 70) {
    return { label: 'Healthy', tone: 'healthy' }
  }
  if (score >= 45) {
    return { label: 'Needs attention', tone: 'attention' }
  }
  return { label: 'Critical', tone: 'critical' }
}
