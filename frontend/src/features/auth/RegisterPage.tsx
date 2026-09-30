import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'

import { useAuth } from './useAuth'

export function RegisterPage() {
  const { user, register } = useAuth()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const registerMutation = useMutation({
    mutationFn: () => register(email, fullName, password),
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    registerMutation.mutate()
  }

  if (user !== null) {
    return <Navigate to="/" replace />
  }

  return (
    <main className="card">
      <h1>Create an account</h1>

      <form onSubmit={handleSubmit}>
        <label htmlFor="full-name">Full name</label>
        <input
          id="full-name"
          type="text"
          autoComplete="name"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          required
        />

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <button type="submit" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      {registerMutation.isError && (
        <p className="error" role="alert">
          {registerMutation.error.message}
        </p>
      )}

      <p className="hint">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </main>
  )
}
