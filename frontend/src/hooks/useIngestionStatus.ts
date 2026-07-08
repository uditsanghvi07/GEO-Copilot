import { useCallback, useEffect, useState } from 'react'
import type { StageStatus } from '../api/types'
import { api } from '../api/client'

/** Map crawl + playstore ingestion into pipeline-style stage statuses. */
export function useIngestionStatus(productId: number, enabled: boolean) {
  const [stages, setStages] = useState<Record<string, StageStatus>>({})

  const poll = useCallback(async () => {
    const next: Record<string, StageStatus> = {}

    try {
      const crawl = await api.getCrawlStatus(productId)
      next.website_crawler = {
        status:
          crawl.status === 'success'
            ? 'success'
            : crawl.status === 'failed'
              ? 'failed'
              : 'running',
        error_message: crawl.error_message,
      }
    } catch {
      next.website_crawler = { status: 'skipped', error_message: 'No website crawl started' }
    }

    try {
      const play = await api.getPlayStoreStatus(productId)
      next.play_store_analyzer = {
        status:
          play.status === 'success'
            ? 'success'
            : play.status === 'failed'
              ? 'failed'
              : 'running',
        error_message: play.error_message,
      }
    } catch {
      next.play_store_analyzer = {
        status: 'skipped',
        error_message: 'No Play Store audit started',
      }
    }

    setStages(next)
    const done = Object.values(next).every(
      (s) => s.status === 'success' || s.status === 'failed' || s.status === 'skipped',
    )
    return done
  }, [productId])

  useEffect(() => {
    if (!enabled) return
    let active = true
    let timer: ReturnType<typeof setTimeout>

    const run = async () => {
      const done = await poll()
      if (!active) return
      if (!done) timer = setTimeout(run, 3000)
    }

    run()
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [enabled, poll])

  return stages
}
