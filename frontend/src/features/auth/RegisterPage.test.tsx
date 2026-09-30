import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { stubBackend } from '../../test/stubBackend'

const GRACE = {
  id: '22222222-2222-4222-8222-222222222222',
  email: 'grace@example.com',
  full_name: 'Grace Hopper',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
}

async function fillRegistrationForm(user: ReturnType<typeof renderApp>['user']) {
  await user.type(screen.getByLabelText('Full name'), GRACE.full_name)
  await user.type(screen.getByLabelText('Email'), GRACE.email)
  await user.type(screen.getByLabelText('Password'), 'super-secret-1')
  await user.click(screen.getByRole('button', { name: 'Create account' }))
}

describe('registering', () => {
  it('signs the new account in straight away', async () => {
    stubBackend({
      'POST /auth/register': () => ({ status: 201, body: GRACE }),
      'POST /auth/login': () => ({ status: 200, body: { access_token: 'a-token', token_type: 'bearer' } }),
      'GET /auth/me': () => ({ status: 200, body: GRACE }),
    })
    const { user } = renderApp('/register')

    await fillRegistrationForm(user)

    expect(await screen.findByRole('heading', { name: 'Signed in' })).toBeInTheDocument()
    expect(screen.getByText(GRACE.email)).toBeInTheDocument()
  })

  it('reports an email that is already taken', async () => {
    stubBackend({
      'POST /auth/register': () => ({ status: 409, body: { detail: 'Email already registered' } }),
    })
    const { user } = renderApp('/register')

    await fillRegistrationForm(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Email already registered')
  })

  it('reports field validation errors from the backend', async () => {
    stubBackend({
      'POST /auth/register': () => ({
        status: 422,
        body: { detail: [{ msg: 'String should have at least 8 characters' }] },
      }),
    })
    const { user } = renderApp('/register')

    await fillRegistrationForm(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'String should have at least 8 characters',
    )
  })
})
