import { useAuth } from './useAuth'

/** Temporary landing page; it exists to prove the authenticated call works. */
export function AccountPage() {
  const { user, logout } = useAuth()

  return (
    <main className="card">
      <h1>Signed in</h1>

      <dl>
        <dt>Name</dt>
        <dd>{user?.full_name}</dd>
        <dt>Email</dt>
        <dd>{user?.email}</dd>
      </dl>

      <button type="button" onClick={logout}>
        Sign out
      </button>
    </main>
  )
}
