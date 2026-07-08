import type { StageStatus } from '../api/types'
import { PIPELINE_STEPS, type PipelineStepKey } from '../constants/pipelineSteps'

export type StepState = 'done' | 'running' | 'pending' | 'failed' | 'skipped'

export function resolveStepState(status?: string): StepState {
  if (status === 'success' || status === 'partial') return 'done'
  if (status === 'running') return 'running'
  if (status === 'failed') return 'failed'
  if (status === 'skipped') return 'skipped'
  return 'pending'
}

function statusesForStep(
  step: (typeof PIPELINE_STEPS)[number],
  stageStatuses: Record<string, StageStatus>,
): string[] {
  const keys = [
    step.key,
    ...('relatedKeys' in step && step.relatedKeys ? step.relatedKeys : []),
  ]
  return keys.map((k) => stageStatuses[k]?.status).filter(Boolean) as string[]
}

export function combinedStepState(
  step: (typeof PIPELINE_STEPS)[number],
  stageStatuses: Record<string, StageStatus>,
): StepState {
  const statuses = statusesForStep(step, stageStatuses)
  if (statuses.length === 0) return 'pending'
  if (statuses.some((s) => s === 'running')) return 'running'
  if (statuses.every((s) => s === 'success' || s === 'partial')) return 'done'
  if (statuses.some((s) => s === 'failed')) return 'failed'
  if (statuses.every((s) => s === 'skipped')) return 'skipped'
  if (statuses.some((s) => s === 'success' || s === 'partial')) return 'running'
  return 'pending'
}

export function getActivePipelineStep(
  stageStatuses: Record<string, StageStatus>,
): PipelineStepKey | null {
  for (const step of PIPELINE_STEPS) {
    const state = combinedStepState(step, stageStatuses)
    if (state === 'running' || state === 'pending') {
      return step.key
    }
  }
  return null
}

export function getPipelineProgress(stageStatuses: Record<string, StageStatus>) {
  let completed = 0
  let running = 0
  let failed = 0

  for (const step of PIPELINE_STEPS) {
    const state = combinedStepState(step, stageStatuses)
    if (state === 'done' || state === 'skipped') completed++
    if (state === 'running') running++
    if (state === 'failed') failed++
  }

  const total = PIPELINE_STEPS.length
  const percent = Math.round((completed / total) * 100)

  return { completed, total, percent, running, failed, active: getActivePipelineStep(stageStatuses) }
}

export function isPipelineFinished(
  overallStatus?: string,
  stageStatuses?: Record<string, StageStatus>,
): boolean {
  if (overallStatus === 'success' || overallStatus === 'partial' || overallStatus === 'failed') {
    return true
  }
  if (!stageStatuses || Object.keys(stageStatuses).length === 0) return false
  return PIPELINE_STEPS.every((step) => {
    const state = combinedStepState(step, stageStatuses)
    return state === 'done' || state === 'failed' || state === 'skipped'
  })
}

export function rawStatusForStep(
  step: (typeof PIPELINE_STEPS)[number],
  stageStatuses: Record<string, StageStatus>,
): string | undefined {
  const statuses = statusesForStep(step, stageStatuses)
  if (statuses.some((s) => s === 'running')) return 'running'
  if (statuses.every((s) => s === 'success' || s === 'partial')) return 'success'
  if (statuses.some((s) => s === 'failed')) return 'failed'
  if (statuses.every((s) => s === 'skipped')) return 'skipped'
  return statuses[0]
}
