import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import App from '../App'
import { AuthProvider } from '../features/auth/AuthProvider'

/**
 * Renders the real router and providers so tests exercise navigation and the
 * auth flow rather than a component in isolation.
 */
export function renderApp(initialPath: string) {
  const queryClient = new QueryClient({
    // Retries would turn an expected failure into a multi-second test.
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  const view = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )

  return { ...view, user: userEvent.setup() }
}
