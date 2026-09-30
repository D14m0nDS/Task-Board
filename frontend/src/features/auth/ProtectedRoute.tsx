import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from './useAuth'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <p className="status">Loading…</p>
  }

  // This only decides what to render. The backend still authorises every
  // request, so hiding a route is convenience rather than security.
  if (user === null) {
    return <Navigate to="/login" replace />
  }

  return children
}
