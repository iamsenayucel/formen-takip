// Pinned so date-formatting tests are deterministic regardless of the machine
// running them — matches this app's business timezone (Europe/Istanbul is
// UTC+3 year-round, so this never rolls a UTC-midnight ISO date backwards).
process.env.TZ = 'Europe/Istanbul'

import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// We don't enable Vitest's `globals: true` (explicit imports are preferred
// here), so Testing Library's own auto-cleanup — which hooks into a global
// afterEach — never registers. Without this, DOM trees from one test leak
// into the next within the same file.
afterEach(() => {
  cleanup()
})
