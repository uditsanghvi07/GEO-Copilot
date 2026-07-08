import { describe, expect, it } from 'vitest'
import {
  combinedStepState,
  getPipelineProgress,
  isPipelineFinished,
} from './pipelineProgress'
import { PIPELINE_STEPS } from '../constants/pipelineSteps'

describe('pipelineProgress', () => {
  it('marks first step active when pipeline just started', () => {
    const progress = getPipelineProgress({})
    expect(progress.completed).toBe(0)
    expect(progress.active).toBe('website_crawler')
  })

  it('combines content_faq and content_meta_description', () => {
    const state = combinedStepState(PIPELINE_STEPS[5], {
      content_faq: { status: 'success' },
      content_meta_description: { status: 'running' },
    })
    expect(state).toBe('running')
  })

  it('detects pipeline finished from overall status', () => {
    expect(isPipelineFinished('success', {})).toBe(true)
    expect(isPipelineFinished('running', {})).toBe(false)
  })
})
