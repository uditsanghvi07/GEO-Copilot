import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check } from 'lucide-react'
import type { ActionPlanStep } from '../api/types'

interface ActionPlanChecklistProps {
  steps: ActionPlanStep[]
}

export function ActionPlanChecklist({ steps }: ActionPlanChecklistProps) {
  const [checked, setChecked] = useState<Record<number, boolean>>({})

  if (steps.length === 0) {
    return (
      <p className="text-sm text-muted font-body">
        No action plan available yet. Run a full audit to generate recommendations.
      </p>
    )
  }

  return (
    <ol className="space-y-3">
      {steps.map((step, index) => {
        const isChecked = checked[index]
        return (
          <li key={`${step.component}-${index}`}>
            <button
              type="button"
              onClick={() =>
                setChecked((prev) => ({ ...prev, [index]: !prev[index] }))
              }
              className="w-full flex items-start gap-3 text-left group"
            >
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors ${
                  isChecked
                    ? 'border-accent bg-accent-muted'
                    : 'border-border group-hover:border-accent/40'
                }`}
              >
                <AnimatePresence>
                  {isChecked && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                    >
                      <Check size={12} className="text-accent" />
                    </motion.span>
                  )}
                </AnimatePresence>
              </span>
              <div className="min-w-0">
                <p
                  className={`text-sm font-body ${isChecked ? 'text-muted line-through' : 'text-text'}`}
                >
                  {step.step}
                </p>
                <p className="text-xs text-muted mt-0.5 font-mono-num">
                  +{step.estimated_point_impact} pts · {step.component}
                </p>
              </div>
            </button>
          </li>
        )
      })}
    </ol>
  )
}
