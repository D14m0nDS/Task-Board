import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Auto cleanup only registers itself when Vitest globals are enabled, and this
// project imports test helpers explicitly instead.
afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.unstubAllGlobals()
})
