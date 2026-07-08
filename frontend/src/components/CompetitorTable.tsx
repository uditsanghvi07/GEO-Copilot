import { Check, X } from 'lucide-react'
import type { CompareStatus, ScoreBreakdown } from '../api/types'
import { getCompetitorDisplayName } from '../utils/displayNames'
import { BREAKDOWN_KEYS } from '../utils/score'

interface CompetitorTableProps {
  comparison: CompareStatus
  productName: string
  ourBreakdown?: ScoreBreakdown
}

function hasFeature(
  breakdown: ScoreBreakdown | undefined,
  key: string,
): boolean {
  const component = breakdown?.[key as keyof ScoreBreakdown]
  if (!component || typeof component !== 'object') return false
  return (component.earned ?? 0) > 0
}

export function CompetitorTable({
  comparison,
  productName,
  ourBreakdown,
}: CompetitorTableProps) {
  const competitors = comparison.competitor_scores ?? []
  const ourLabel = comparison.our_product_name ?? productName

  const ourScoreBreakdown = comparison.our_breakdown ?? ourBreakdown
  const ourTotal = comparison.our_score ?? ourBreakdown?.total

  if (competitors.length === 0) {
    return (
      <p className="text-sm text-muted font-body">
        No competitor comparison yet. Add competitor URLs and run a full audit.
      </p>
    )
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted font-body">
        Comparing <span className="text-text font-medium">{ourLabel}</span> against{' '}
        {competitors.map((comp, i) => (
          <span key={comp.competitor_url ?? comp.url ?? i}>
            {i > 0 && (i === competitors.length - 1 ? ', and ' : ', ')}
            <span className="text-text font-medium">
              {getCompetitorDisplayName(comp, i)}
            </span>
          </span>
        ))}
        .
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm font-body">
          <thead>
            <tr className="text-left text-muted border-b border-border">
              <th className="py-3 pr-4 font-medium">Dimension</th>
              <th className="py-3 px-4 font-medium">{ourLabel}</th>
              {competitors.map((comp, i) => (
                <th key={comp.url ?? comp.competitor_url ?? i} className="py-3 px-4 font-medium">
                  {getCompetitorDisplayName(comp, i)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {BREAKDOWN_KEYS.map(({ key, label }) => (
              <tr key={key} className="border-b border-border/60">
                <td className="py-3 pr-4 text-text">{label}</td>
                <td className="py-3 px-4">
                  <Indicator present={hasFeature(ourScoreBreakdown, key)} />
                </td>
                {competitors.map((comp, i) => (
                  <td key={`${key}-${comp.url ?? comp.competitor_url ?? i}`} className="py-3 px-4">
                    <Indicator
                      present={hasFeature(comp.score_breakdown, key)}
                    />
                  </td>
                ))}
              </tr>
            ))}
            <tr className="border-b border-border/60">
              <td className="py-3 pr-4 text-text">GEO score</td>
              <td className="py-3 px-4 font-mono-num text-accent">
                {ourTotal ?? '—'}
              </td>
              {competitors.map((comp, i) => (
                <td key={`score-${comp.url ?? comp.competitor_url ?? i}`} className="py-3 px-4 font-mono-num">
                  {comp.geo_score ?? '—'}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {comparison.narrative_summary && (
        <div className="glass-card p-4">
          <h4 className="font-heading text-sm font-semibold mb-2">
            Summary — {ourLabel}
          </h4>
          <p className="text-sm text-muted font-body leading-relaxed">
            {comparison.narrative_summary}
          </p>
        </div>
      )}

      {comparison.improvement_plan.length > 0 && (
        <div>
          <h4 className="font-heading text-sm font-semibold mb-3">
            Improvement plan for {ourLabel}
          </h4>
          <ol className="space-y-2 list-decimal list-inside text-sm text-muted font-body">
            {comparison.improvement_plan.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

function Indicator({ present }: { present: boolean }) {
  return present ? (
    <span className="inline-flex items-center gap-1 text-accent">
      <Check size={14} aria-hidden />
      <span className="sr-only">Present</span>
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-coral">
      <X size={14} aria-hidden />
      <span className="text-xs">missing</span>
    </span>
  )
}
