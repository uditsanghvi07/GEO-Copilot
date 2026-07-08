import { motion } from 'framer-motion'
import { Check, Circle, Loader2, X } from 'lucide-react'
import type { StageStatus } from '../api/types'
import { PIPELINE_STEPS } from '../constants/pipelineSteps'
import { formatCompetitorList } from '../utils/displayNames'
import { combinedStepState, rawStatusForStep, resolveStepState } from '../utils/pipelineProgress'

interface JobStatusProps {
  stageStatuses: Record<string, StageStatus>
  overallStatus?: string
  productName?: string
  competitorNames?: string[]
}

function stepIcon(status?: string) {
  const state = resolveStepState(status)
  if (state === 'done') {
    return <Check size={14} className="text-accent" aria-hidden />
  }
  if (state === 'failed') {
    return <X size={14} className="text-coral" aria-hidden />
  }
  if (state === 'running') {
    return <Loader2 size={14} className="text-accent animate-spin" aria-hidden />
  }
  if (state === 'skipped') {
    return <Circle size={10} className="text-muted" aria-hidden />
  }
  return <Circle size={10} className="text-border" aria-hidden />
}

export function JobStatus({
  stageStatuses,
  overallStatus,
  productName,
  competitorNames = [],
}: JobStatusProps) {
  const competitorLabel =
    competitorNames.length > 0
      ? `Comparing ${productName ?? 'your product'} vs ${formatCompetitorList(competitorNames)}`
      : 'Comparing competitors'

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-heading text-base font-semibold">Pipeline status</h3>
          {productName && (
            <p className="text-xs text-muted font-body mt-0.5">{productName}</p>
          )}
        </div>
        {overallStatus && (
          <span className="font-mono-num text-xs text-muted uppercase tracking-wide">
            {overallStatus}
          </span>
        )}
      </div>
      <ol className="space-y-3" aria-label="Pipeline progress steps">
        {PIPELINE_STEPS.map((step, index) => {
          const state = combinedStepState(step, stageStatuses)
          const isActive = state === 'done'
          const isRunning = state === 'running'
          const isFailed = state === 'failed'
          const isSkipped = state === 'skipped'

          return (
            <motion.li
              key={step.key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-start gap-3"
            >
              <span
                className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded-full border ${
                  isActive
                    ? 'border-accent/40 bg-accent-muted'
                    : isRunning
                      ? 'border-accent/50 bg-accent-muted'
                      : isFailed
                        ? 'border-coral/40 bg-coral-muted'
                        : 'border-border bg-bg'
                }`}
              >
                {stepIcon(rawStatusForStep(step, stageStatuses))}
              </span>
              <div className="min-w-0 flex-1">
                <p
                  className={`text-sm font-body ${
                    isActive
                      ? 'text-accent'
                      : isRunning
                        ? 'text-text'
                        : isFailed
                          ? 'text-coral'
                          : isSkipped
                            ? 'text-muted'
                            : 'text-muted'
                  }`}
                >
                  {step.key === 'competitor' ? competitorLabel : step.label}
                  {isSkipped && (
                    <span className="ml-2 text-xs text-muted">skipped</span>
                  )}
                </p>
                {stageStatuses[step.key]?.error_message && (
                  <p className="text-xs text-muted mt-0.5">
                    {stageStatuses[step.key]?.error_message}
                  </p>
                )}
              </div>
            </motion.li>
          )
        })}
      </ol>
    </div>
  )
}
