import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import type { GeneratedContent } from '../api/types'
import { CopyButton } from './CopyButton'

type ContentType = 'faq' | 'blog' | 'meta' | 'campaign'

interface ContentGeneratorPanelProps {
  open: boolean
  contentType: ContentType | null
  productName?: string
  loading: boolean
  result: GeneratedContent | null
  error: string | null
  onClose: () => void
  onGenerate: (instructions: string) => void
}

const LABELS: Record<ContentType, string> = {
  faq: 'Generate FAQ',
  blog: 'Generate blog post',
  meta: 'Generate meta description',
  campaign: 'Generate campaign bundle',
}

export function ContentGeneratorPanel({
  open,
  contentType,
  productName,
  loading,
  result,
  error,
  onClose,
  onGenerate,
}: ContentGeneratorPanelProps) {
  const [instructions, setInstructions] = useState('')

  const handleClose = () => {
    setInstructions('')
    onClose()
  }

  return (
    <AnimatePresence>
      {open && contentType && (
        <>
          <motion.button
            type="button"
            aria-label="Close panel"
            className="fixed inset-0 bg-bg/70 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-label={LABELS[contentType]}
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md glass-panel-strong border-y-0 border-r-0 flex flex-col"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div>
                <h2 className="font-heading text-base font-semibold">
                  {LABELS[contentType]}
                </h2>
                {productName && (
                  <p className="text-xs text-muted font-body mt-0.5">
                    For {productName}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={handleClose}
                className="p-2 rounded-md text-muted hover:text-text"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              <div>
                <label
                  htmlFor="extra-instructions"
                  className="block text-sm text-muted mb-2 font-body"
                >
                  Extra instructions (optional)
                </label>
                <textarea
                  id="extra-instructions"
                  rows={4}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="Add context or tone guidance for the generator"
                  className="w-full bg-bg hairline-border rounded-md px-3 py-2 text-sm text-text placeholder:text-muted/70 focus:border-accent/50 focus:ring-1 focus:ring-accent/30 resize-none"
                />
              </div>

              <button
                type="button"
                disabled={loading}
                onClick={() => onGenerate(instructions)}
                className={`w-full py-2.5 rounded-md text-sm font-medium font-body transition-colors ${
                  loading
                    ? 'bg-accent/20 text-accent animate-pulse cursor-wait'
                    : 'bg-accent text-bg hover:bg-accent/90'
                }`}
              >
                {loading ? 'Generating…' : LABELS[contentType]}
              </button>

              {error && (
                <p className="text-sm text-coral font-body" role="alert">
                  {error}
                </p>
              )}

              {result && (
                <div className="bg-bg hairline-border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted font-mono-num uppercase">
                      {result.content_type}
                    </span>
                    <CopyButton text={result.content_body} />
                  </div>
                  <pre className="text-sm text-text font-body whitespace-pre-wrap leading-relaxed">
                    {result.content_body}
                  </pre>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
