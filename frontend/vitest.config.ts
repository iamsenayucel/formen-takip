import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Playwright smoke suite (scripts/smoke/*.spec.ts) uses the same .spec.ts
// naming convention, so `include` is scoped to src/ to avoid Vitest picking
// up and trying to run browser-only Playwright specs under jsdom.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/main.tsx', 'src/vite-env.d.ts', 'src/test/**', 'src/**/*.d.ts'],
      // Project-wide coverage is intentionally partial for now (most pages
      // and chart components have no tests yet — see the test-plan report).
      // A blanket global floor would be fragile: it starts failing the
      // moment anyone adds any new untested file, unrelated to what they
      // touched. Instead, floors are scoped to the areas that already carry
      // real coverage and matter most for correctness (business-rule
      // helpers and auth), set a few points below today's baseline so they
      // catch a genuine regression without being flaky on a one-line change.
      thresholds: {
        'src/lib/**': { statements: 80, branches: 65, functions: 65, lines: 80 },
        'src/auth/**': { statements: 80, branches: 40, functions: 90, lines: 80 },
      },
    },
  },
})
