import type { CompetitorScore } from '../api/types'

const GENERIC_COMPETITOR_HOSTS = ['play.google.com', 'apps.apple.com', 'www.play.google.com']

export function isGenericCompetitorName(name: string | undefined | null): boolean {
  if (!name || name === 'competitor') return true
  const lower = name.toLowerCase()
  return GENERIC_COMPETITOR_HOSTS.some((host) => lower === host || lower.includes(host))
}

export function getCompetitorDisplayName(
  comp: CompetitorScore,
  index: number,
): string {
  const signals = comp.signals as Record<string, unknown> | undefined
  const fromSignals =
    (typeof signals?.app_title === 'string' && signals.app_title) ||
    (typeof signals?.title === 'string' && signals.title) ||
    null

  if (fromSignals) return fromSignals

  const stored = comp.competitor_name ?? comp.name
  if (stored && !isGenericCompetitorName(stored)) return stored

  if (stored) return stored

  return `Competitor ${index + 1}`
}

export function formatCompetitorList(names: string[]): string {
  if (names.length === 0) return 'competitors'
  if (names.length === 1) return names[0]
  if (names.length === 2) return `${names[0]} and ${names[1]}`
  return `${names.slice(0, -1).join(', ')}, and ${names[names.length - 1]}`
}
