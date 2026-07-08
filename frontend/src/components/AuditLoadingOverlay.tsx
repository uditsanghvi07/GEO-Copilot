import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, Loader2, Sparkles, X } from 'lucide-react'
import type { StageStatus } from '../api/types'
import { tipsForStage } from '../constants/geoTips'
import { PIPELINE_STEPS } from '../constants/pipelineSteps'
import { formatCompetitorList } from '../utils/displayNames'
import {
  combinedStepState,
  getPipelineProgress,
  type StepState,
} from '../utils/pipelineProgress'
import { useReducedMotion } from '../hooks/useReducedMotion'

interface AuditLoadingOverlayProps {
  open: boolean
  productName: string
  competitorNames?: string[]
  stageStatuses: Record<string, StageStatus>
  overallStatus?: string
}

const TIP_INTERVAL_MS = 4200

const ACCENT_GRADIENT =
  'linear-gradient(135deg, var(--color-accent) 0%, var(--color-violet) 55%, var(--color-coral) 100%)'

export function AuditLoadingOverlay({
  open,
  productName,
  competitorNames = [],
  stageStatuses,
  overallStatus,
}: AuditLoadingOverlayProps) {
  const reducedMotion = useReducedMotion()
  const progress = getPipelineProgress(stageStatuses)
  const tips = useMemo(() => tipsForStage(progress.active), [progress.active])
  const [tipIndex, setTipIndex] = useState(0)

  useEffect(() => {
    if (!open) {
      setTipIndex(0)
      return
    }
    const id = window.setInterval(() => {
      setTipIndex((i) => (i + 1) % tips.length)
    }, TIP_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [open, tips.length, progress.active])

  useEffect(() => {
    setTipIndex(0)
  }, [progress.active])

  const currentTip = tips[tipIndex] ?? tips[0]
  const competitorLabel =
    competitorNames.length > 0 ? formatCompetitorList(competitorNames) : null

  const tipMotion = reducedMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, scale: 0.88, y: 14, filter: 'blur(6px)' },
        animate: { opacity: 1, scale: 1, y: 0, filter: 'blur(0px)' },
        exit: { opacity: 0, scale: 1.06, y: -10, filter: 'blur(4px)' },
      }

  return (
    <AnimatePresence mode="wait">
      {open ? (
        <motion.div
          key="audit-overlay"
          role="dialog"
          aria-modal="true"
          aria-label={`GEO audit running for ${productName}`}
          aria-busy="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
        >
          <motion.div
            className="absolute inset-0 bg-bg/85 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {!reducedMotion && (
            <>
              <motion.div
                className="absolute w-[min(520px,90vw)] h-[min(520px,90vw)] rounded-full opacity-30 pointer-events-none"
                style={{
                  background:
                    'radial-gradient(circle, color-mix(in srgb, var(--color-accent) 35%, transparent), transparent 70%)',
                }}
                animate={{ scale: [1, 1.12, 1], opacity: [0.22, 0.38, 0.22] }}
                transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
              />
              <motion.div
                className="absolute w-[min(400px,80vw)] h-[min(400px,80vw)] rounded-full opacity-20 pointer-events-none"
                style={{
                  background:
                    'radial-gradient(circle, color-mix(in srgb, var(--color-violet) 40%, transparent), transparent 68%)',
                }}
                animate={{ scale: [1.08, 0.94, 1.08] }}
                transition={{ duration: 6.5, repeat: Infinity, ease: 'easeInOut' }}
              />
            </>
          )}

          <motion.div
            className="relative w-full max-w-2xl glass-panel-strong overflow-hidden"
            initial={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.97, y: -12 }}
            transition={{ type: 'spring', stiffness: 260, damping: 28 }}
          >
            <div
              className="absolute inset-x-0 top-0 h-1"
              style={{ background: ACCENT_GRADIENT }}
            />

            <div className="p-6 sm:p-8 space-y-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 text-accent mb-2">
                    <Sparkles size={16} aria-hidden />
                    <span className="text-xs font-mono-num uppercase tracking-widest">
                      AI GEO Copilot
                    </span>
                  </div>
                  <motion.h2
                    className="font-heading text-xl sm:text-2xl font-semibold text-text"
                    animate={reducedMotion ? undefined : { scale: [1, 1.02, 1] }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    Auditing {productName}
                  </motion.h2>
                  {competitorLabel && (
                    <p className="text-xs text-muted font-body mt-1.5">
                      Including comparison vs {competitorLabel}
                    </p>
                  )}
                </div>
                <motion.div
                  className="flex h-12 w-12 items-center justify-center rounded-full border border-accent/30 bg-accent-muted"
                  animate={reducedMotion ? undefined : { rotate: 360 }}
                  transition={{ duration: 2.4, repeat: Infinity, ease: 'linear' }}
                >
                  <Loader2 size={22} className="text-accent" aria-hidden />
                </motion.div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-body">
                  <span className="text-muted">Pipeline progress</span>
                  <span className="font-mono-num text-accent">
                    {progress.completed}/{progress.total}
                    <span className="text-muted ml-2">({progress.percent}%)</span>
                  </span>
                </div>
                <div className="h-2 rounded-full bg-border overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: ACCENT_GRADIENT }}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(progress.percent, 4)}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                  />
                </div>
              </div>

              <div
                className="relative min-h-[108px] sm:min-h-[96px] rounded-lg px-5 py-4 overflow-hidden"
                style={{
                  background:
                    'linear-gradient(135deg, color-mix(in srgb, var(--color-accent) 8%, transparent), color-mix(in srgb, var(--color-violet) 10%, transparent))',
                  border: '1px solid color-mix(in srgb, var(--color-accent) 18%, transparent)',
                }}
              >
                <p className="text-[10px] uppercase tracking-wider text-muted font-mono-num mb-3">
                  GEO insight
                </p>
                <AnimatePresence mode="wait">
                  <motion.p
                    key={`${progress.active ?? 'general'}-${tipIndex}`}
                    className="text-sm sm:text-base text-text font-body leading-relaxed pr-2"
                    {...tipMotion}
                    transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
                  >
                    {currentTip}
                  </motion.p>
                </AnimatePresence>
              </div>

              <ol className="space-y-2.5" aria-label="Audit pipeline checkpoints">
                {PIPELINE_STEPS.map((step, index) => {
                  const state = combinedStepState(step, stageStatuses)
                  const label =
                    step.key === 'competitor' && competitorLabel
                      ? `Comparing vs ${competitorLabel}`
                      : step.label

                  return (
                    <motion.li
                      key={step.key}
                      initial={reducedMotion ? false : { opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.04 }}
                      className="flex items-center gap-3"
                    >
                      <CheckpointIcon state={state} reducedMotion={reducedMotion} />
                      <span
                        className={`text-sm font-body flex-1 ${
                          state === 'done'
                            ? 'text-accent'
                            : state === 'running'
                              ? 'text-text'
                              : state === 'failed'
                                ? 'text-coral'
                                : 'text-muted'
                        }`}
                      >
                        {label}
                        {state === 'running' && (
                          <motion.span
                            className="inline-block ml-1 text-accent"
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{ duration: 1.2, repeat: Infinity }}
                          >
                            …
                          </motion.span>
                        )}
                      </span>
                      <StatusPill state={state} />
                    </motion.li>
                  )
                })}
              </ol>

              {overallStatus && (
                <p className="text-center text-xs text-muted font-mono-num uppercase tracking-wide">
                  {overallStatus}
                </p>
              )}
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}

function CheckpointIcon({
  state,
  reducedMotion,
}: {
  state: StepState
  reducedMotion: boolean
}) {
  if (state === 'done') {
    return (
      <motion.span
        className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-muted border border-accent/40"
        initial={reducedMotion ? false : { scale: 0.6 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 18 }}
      >
        <Check size={13} className="text-accent" aria-hidden />
      </motion.span>
    )
  }
  if (state === 'failed') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-coral-muted border border-coral/40">
        <X size={13} className="text-coral" aria-hidden />
      </span>
    )
  }
  if (state === 'running') {
    return (
      <motion.span
        className="flex h-6 w-6 items-center justify-center rounded-full border border-accent/50 bg-accent-muted"
        animate={reducedMotion ? undefined : { scale: [1, 1.12, 1] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
      >
        <Loader2 size={13} className="text-accent animate-spin" aria-hidden />
      </motion.span>
    )
  }
  if (state === 'skipped') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-border bg-bg">
        <span className="text-[10px] text-muted font-mono-num">—</span>
      </span>
    )
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-border bg-bg">
      <span className="h-1.5 w-1.5 rounded-full bg-border" />
    </span>
  )
}

function StatusPill({ state }: { state: StepState }) {
  const styles: Record<StepState, string> = {
    done: 'text-accent bg-accent-muted border-accent/25',
    running: 'text-text bg-violet-muted border-violet/25',
    pending: 'text-muted bg-bg border-border',
    failed: 'text-coral bg-coral-muted border-coral/25',
    skipped: 'text-muted bg-bg border-border',
  }
  const labels: Record<StepState, string> = {
    done: 'done',
    running: 'active',
    pending: 'waiting',
    failed: 'failed',
    skipped: 'skipped',
  }
  return (
    <span
      className={`text-[10px] font-mono-num uppercase px-2 py-0.5 rounded-full border ${styles[state]}`}
    >
      {labels[state]}
    </span>
  )
}
