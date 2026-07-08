import { describe, expect, it } from 'vitest'
import { formatDateTime, parseApiDate } from './format'

describe('format IST timezone', () => {
  it('treats naive API datetime as UTC', () => {
    const date = parseApiDate('2026-07-07T10:36:00')
    expect(date?.toISOString()).toBe('2026-07-07T10:36:00.000Z')
  })

  it('formats UTC timestamp in India timezone', () => {
    // 10:36 UTC = 16:06 IST (4:06 PM)
    const formatted = formatDateTime('2026-07-07T10:36:00')
    expect(formatted).toMatch(/4:06/)
    expect(formatted).toMatch(/pm/i)
    expect(formatted).toMatch(/GMT\+5:30|IST/i)
  })
})
