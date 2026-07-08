import { useEffect, useRef } from 'react'

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  enabled: boolean,
  onData: (data: T) => void,
  shouldStop?: (data: T) => boolean,
) {
  const onDataRef = useRef(onData)
  const shouldStopRef = useRef(shouldStop)

  useEffect(() => {
    onDataRef.current = onData
  }, [onData])

  useEffect(() => {
    shouldStopRef.current = shouldStop
  }, [shouldStop])

  useEffect(() => {
    if (!enabled) return

    let active = true
    let timer: ReturnType<typeof setTimeout>

    const poll = async () => {
      try {
        const data = await fetcher()
        if (!active) return
        onDataRef.current(data)
        if (shouldStopRef.current?.(data)) return
      } catch {
        // Polling endpoints may return 404/202 while jobs run — keep polling.
      }
      if (active) {
        timer = setTimeout(poll, intervalMs)
      }
    }

    poll()

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [enabled, fetcher, intervalMs])
}
