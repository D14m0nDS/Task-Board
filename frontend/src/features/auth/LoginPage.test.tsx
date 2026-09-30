import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { stubBackend } from '../../test/stubBackend'

const ADA = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'ada@example.com',
  full_name: 'Ada Lovelace',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
}

describe('signing in', () => {
  it('shows the message the backend returned', async () => {
    stubBackend({
      'POST /auth/login': () => ({ status: 401, body: { detail: 'Incorrect email or password' } }),
    })
    const { user } = renderApp('/login')

    await user.type(screen.getByLabelText('Email'), ADA.email)
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password')
  })

  it('lands on the account page and shows the authenticated user', async () => {
    stubBackend({
      'POST /auth/login': () => ({ status: 200, body: { access_token: 'a-token', token_type: 'bearer' } }),
      'GET /auth/me': () => ({ status: 200, body: ADA }),
    })
    const { user } = renderApp('/login')

    await user.type(screen.getByLabelText('Email'), ADA.email)
    await user.type(screen.getByLabelText('Password'), 'super-secret-1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Signed in' })).toBeInTheDocument()
    expect(screen.getByText(ADA.full_name)).toBeInTheDocument()
  })

  it('stores the token so the session survives a reload', async () => {
    stubBackend({
      'POST /auth/login': () => ({ status: 200, body: { access_token: 'a-token', token_type: 'bearer' } }),
      'GET /auth/me': () => ({ status: 200, body: ADA }),
    })
    const { user } = renderApp('/login')

    await user.type(screen.getByLabelText('Email'), ADA.email)
    await user.type(screen.getByLabelText('Password'), 'super-secret-1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await screen.findByRole('heading', { name: 'Signed in' })

    expect(localStorage.getItem('taskboard.access_token')).toBe('a-token')
  })

  it('sends the token as a bearer header on authenticated requests', async () => {
    const fetchStub = stubBackend({
      'POST /auth/login': () => ({ status: 200, body: { access_token: 'a-token', token_type: 'bearer' } }),
      'GET /auth/me': () => ({ status: 200, body: ADA }),
    })
    const { user } = renderApp('/login')

    await user.type(screen.getByLabelText('Email'), ADA.email)
    await user.type(screen.getByLabelText('Password'), 'super-secret-1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await screen.findByRole('heading', { name: 'Signed in' })

    const meCall = fetchStub.mock.calls.find(([url]) => String(url).endsWith('/auth/me'))
    expect(meCall?.[1]?.headers).toMatchObject({ Authorization: 'Bearer a-token' })
  })
})

describe('the account page', () => {
  it('redirects an anonymous visitor to the login page', async () => {
    stubBackend({})
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('discards a stored token the backend rejects', async () => {
    localStorage.setItem('taskboard.access_token', 'expired-token')
    stubBackend({
      'GET /auth/me': () => ({ status: 401, body: { detail: 'Could not validate credentials' } }),
    })
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(localStorage.getItem('taskboard.access_token')).toBeNull()
  })

  it('signs out and returns to the login page', async () => {
    localStorage.setItem('taskboard.access_token', 'a-token')
    stubBackend({ 'GET /auth/me': () => ({ status: 200, body: ADA }) })
    const { user } = renderApp('/')

    await user.click(await screen.findByRole('button', { name: 'Sign out' }))

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(localStorage.getItem('taskboard.access_token')).toBeNull()
  })
})
