import { describe, expect, it } from 'vitest'
import type { CompetitorScore } from '../api/types'
import {
  formatCompetitorList,
  getCompetitorDisplayName,
  isGenericCompetitorName,
} from './displayNames'

describe('displayNames', () => {
  it('detects generic play store hostnames', () => {
    expect(isGenericCompetitorName('play.google.com')).toBe(true)
    expect(isGenericCompetitorName('Ho Bible')).toBe(false)
  })

  it('prefers app title from signals over hostname', () => {
    const comp: CompetitorScore = {
      competitor_name: 'play.google.com',
      signals: { app_title: 'Ho Bible' },
    }
    expect(getCompetitorDisplayName(comp, 0)).toBe('Ho Bible')
  })

  it('formats competitor lists for pipeline labels', () => {
    expect(formatCompetitorList(['Ho Bible'])).toBe('Ho Bible')
    expect(formatCompetitorList(['Ho Bible', 'FitTrack'])).toBe('Ho Bible and FitTrack')
  })
})
