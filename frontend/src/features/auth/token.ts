const STORAGE_KEY = 'taskboard.access_token'

// localStorage keeps the session across refreshes but is readable by any
// script on the page. An httpOnly cookie would resist XSS, at the cost of
// CSRF protection and backend changes; revisit before production.
export function readToken(): string | null {
  return localStorage.getItem(STORAGE_KEY)
}

export function writeToken(token: string): void {
  localStorage.setItem(STORAGE_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(STORAGE_KEY)
}
