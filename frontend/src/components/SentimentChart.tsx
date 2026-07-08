import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { ReviewSummary } from '../api/types'

interface SentimentChartProps {
  summary: ReviewSummary
  productName: string
}

const STAR_ROWS = [
  { key: 'five', label: '5 stars', tone: 'var(--color-accent)' },
  { key: 'four', label: '4 stars', tone: 'var(--color-accent)' },
  { key: 'three', label: '3 stars', tone: 'var(--color-muted)' },
  { key: 'two', label: '2 stars', tone: 'var(--color-coral)' },
  { key: 'one', label: '1 star', tone: 'var(--color-coral)' },
] as const

export function SentimentChart({ summary, productName }: SentimentChartProps) {
  const { positive, neutral, negative } = summary.sentiment_counts
  const total = summary.total_reviews || positive + neutral + negative

  const data = [
    { name: 'Positive (4-5★)', value: positive, fill: 'var(--color-accent)' },
    { name: 'Neutral (3★)', value: neutral, fill: 'var(--color-muted)' },
    { name: 'Negative (1-2★)', value: negative, fill: 'var(--color-coral)' },
  ].filter((d) => d.value > 0)

  const pct = (n: number) => (total > 0 ? Math.round((n / total) * 100) : 0)
  const maxStar = Math.max(
    1,
    ...STAR_ROWS.map((r) => summary.rating_distribution[r.key]),
  )

  return (
    <div className="glass-card p-5">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="font-heading text-base font-semibold">
          Review sentiment
        </h3>
        <span className="text-xs text-muted font-body">
          {productName} · Play Store
        </span>
      </div>
      <p className="text-xs text-muted font-body mb-5">
        Based on{' '}
        <span className="font-mono-num text-text">{total}</span> collected
        review{total === 1 ? '' : 's'}
        {summary.average_rating != null && (
          <>
            {' '}
            · average{' '}
            <span className="font-mono-num text-text">
              {summary.average_rating.toFixed(1)}
            </span>
            <span className="text-muted">/5</span>
          </>
        )}
      </p>

      {total === 0 ? (
        <p className="text-sm text-muted font-body">
          No individual review ratings are stored yet for this product.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div>
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={48}
                    outerRadius={70}
                    paddingAngle={2}
                    stroke="none"
                  >
                    {data.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: '6px',
                      color: 'var(--color-text)',
                      fontFamily: 'var(--font-body)',
                      fontSize: 12,
                    }}
                    formatter={(value: number, name) => [
                      `${value} (${pct(value)}%)`,
                      name,
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-1.5 mt-2">
              {[
                { label: 'Positive', count: positive, tone: 'var(--color-accent)' },
                { label: 'Neutral', count: neutral, tone: 'var(--color-muted)' },
                { label: 'Negative', count: negative, tone: 'var(--color-coral)' },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-center gap-2 text-xs"
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: item.tone }}
                  />
                  <span className="text-muted font-body w-16">{item.label}</span>
                  <span className="font-mono-num text-text">{item.count}</span>
                  <span className="font-mono-num text-muted">
                    {pct(item.count)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs text-muted font-body mb-1">
              Rating distribution
            </p>
            {STAR_ROWS.map((row) => {
              const count = summary.rating_distribution[row.key]
              const barPct = (count / maxStar) * 100
              return (
                <div key={row.key} className="flex items-center gap-3 text-xs">
                  <span className="text-muted font-body w-14 shrink-0">
                    {row.label}
                  </span>
                  <div className="flex-1 h-2 rounded-sm bg-border overflow-hidden">
                    <div
                      className="h-full rounded-sm transition-all duration-500"
                      style={{ width: `${barPct}%`, background: row.tone }}
                    />
                  </div>
                  <span className="font-mono-num text-text w-8 text-right">
                    {count}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
