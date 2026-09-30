import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '../../lib/api'
import {
  fetchCurrentUser,
  login as requestLogin,
  register as requestRegister,
} from './api'
import { AuthContext, type AuthContextValue } from './authContext'
import { clearToken, readToken, writeToken } from './token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readToken())
  const queryClient = useQueryClient()

  // The backend is the authority on who the token belongs to, so the user is
  // fetched rather than decoded from the JWT on the client.
  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'currentUser', token],
    queryFn: async () => {
      try {
        return await fetchCurrentUser(token as string)
      } catch (error) {
        // A stored token can be expired or belong to a deleted user. Discard
        // it only when the backend rejects it, never on a network failure.
        if (error instanceof ApiError && error.status === 401) {
          clearToken()
          setToken(null)
        }
        throw error
      }
    },
    enabled: token !== null,
    retry: false,
  })

  const login = useCallback(async (email: string, password: string) => {
    const { access_token: accessToken } = await requestLogin(email, password)
    writeToken(accessToken)
    setToken(accessToken)
  }, [])

  // Registration does not return a token, so the new account is signed in
  // through the normal login path rather than a second code path.
  const register = useCallback(
    async (email: string, fullName: string, password: string) => {
      await requestRegister(email, fullName, password)
      await login(email, password)
    },
    [login],
  )

  const logout = useCallback(() => {
    clearToken()
    setToken(null)
    queryClient.clear()
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: user ?? null,
      isLoading: token !== null && isLoading,
      login,
      register,
      logout,
    }),
    [user, token, isLoading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
