import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import type { ScoreBreakdown } from '../api/types'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { getBreakdownItems } from '../utils/score'

interface GeoScoreRingProps {
  score: number | null
  breakdown?: ScoreBreakdown
  size?: 'sm' | 'lg'
  showLegend?: boolean
  className?: string
}

const SIZE_CONFIG = {
  sm: { diameter: 88, stroke: 5, fontSize: 'text-xl', legend: false },
  lg: { diameter: 180, stroke: 7, fontSize: 'text-5xl', legend: true },
} as const

export function GeoScoreRing({
  score,
  breakdown,
  size = 'sm',
  showLegend,
  className = '',
}: GeoScoreRingProps) {
  const reducedMotion = useReducedMotion()
  const config = SIZE_CONFIG[size]
  const displayScore = score ?? 0
  const radius = (config.diameter - config.stroke) / 2
  const center = config.diameter / 2
  const circumference = 2 * Math.PI * radius
  const sweepArc = circumference * 0.22

  const [animatedScore, setAnimatedScore] = useState(
    reducedMotion ? displayScore : 0,
  )
  const [sweepDone, setSweepDone] = useState(reducedMotion)

  const dashOffset = circumference * (1 - animatedScore / 100)

  const legendItems = useMemo(() => getBreakdownItems(breakdown), [breakdown])
  const shouldShowLegend = showLegend ?? config.legend

  useEffect(() => {
    if (reducedMotion) {
      setAnimatedScore(displayScore)
      setSweepDone(true)
      return
    }

    setAnimatedScore(0)
    setSweepDone(false)

    const sweepTimer = setTimeout(() => setSweepDone(true), 1200)
    return () => clearTimeout(sweepTimer)
  }, [displayScore, reducedMotion])

  useEffect(() => {
    if (!sweepDone || reducedMotion) {
      if (reducedMotion) setAnimatedScore(displayScore)
      return
    }

    const duration = 900
    const start = performance.now()
    let frame: number

    const tick = (now: number) => {
      const elapsed = now - start
      const t = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setAnimatedScore(Math.round(displayScore * eased))
      if (t < 1) frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [sweepDone, displayScore, reducedMotion])

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      <div
        className="relative"
        style={{ width: config.diameter, height: config.diameter }}
        aria-label={
          score == null
            ? 'GEO score not available'
            : `GEO score ${Math.round(animatedScore)} out of 100`
        }
        role="img"
      >
        <svg
          width={config.diameter}
          height={config.diameter}
          viewBox={`0 0 ${config.diameter} ${config.diameter}`}
          className="block"
        >
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="var(--color-border)"
            strokeWidth={config.stroke}
          />

          {!reducedMotion && !sweepDone && (
            <motion.circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth={config.stroke}
              strokeLinecap="round"
              strokeDasharray={`${sweepArc} ${circumference - sweepArc}`}
              initial={{ rotate: -90 }}
              animate={{ rotate: 270 }}
              transition={{ duration: 1.2, ease: 'linear' }}
              style={{ transformOrigin: `${center}px ${center}px` }}
              opacity={0.9}
            />
          )}

          {(sweepDone || reducedMotion) && (
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth={config.stroke}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              transform={`rotate(-90 ${center} ${center})`}
              style={{ transition: reducedMotion ? 'none' : 'stroke-dashoffset 0.08s linear' }}
            />
          )}
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`font-mono-num font-medium text-text ${config.fontSize}`}>
            {score == null ? '—' : Math.round(animatedScore)}
          </span>
          {size === 'lg' && (
            <span className="text-xs text-muted mt-1 font-body">GEO score</span>
          )}
        </div>
      </div>

      {shouldShowLegend && (
        <div className="w-full max-w-xs space-y-2">
          {legendItems.map((item) => {
            const pct = item.max > 0 ? (item.earned / item.max) * 100 : 0
            return (
              <div key={item.key} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted font-body">{item.label}</span>
                  <span className="font-mono-num text-muted">
                    {item.earned}/{item.max}
                  </span>
                </div>
                <div className="h-1 rounded-sm bg-border overflow-hidden">
                  <div
                    className="h-full rounded-sm bg-accent transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
