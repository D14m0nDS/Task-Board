import { apiFetch } from '../../lib/api'

// Field names mirror the backend schemas exactly, so responses need no mapping.
export type User = {
  id: string
  email: string
  full_name: string
  is_active: boolean
  created_at: string
}

export type Token = {
  access_token: string
  token_type: string
}

export function login(email: string, password: string): Promise<Token> {
  return apiFetch<Token>('/auth/login', { method: 'POST', body: { email, password } })
}

export function register(email: string, fullName: string, password: string): Promise<User> {
  return apiFetch<User>('/auth/register', {
    method: 'POST',
    body: { email, full_name: fullName, password },
  })
}

export function fetchCurrentUser(token: string): Promise<User> {
  return apiFetch<User>('/auth/me', { token })
}
