interface StatusPillProps {
  tone: 'healthy' | 'attention' | 'critical' | 'muted'
  label: string
}

const TONE_CLASSES = {
  healthy: 'bg-accent-muted text-accent border-accent/30',
  attention: 'bg-border/60 text-muted border-border',
  critical: 'bg-coral-muted text-coral border-coral/30',
  muted: 'bg-border/40 text-muted border-border',
} as const

export function StatusPill({ tone, label }: StatusPillProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-body border ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  )
}
