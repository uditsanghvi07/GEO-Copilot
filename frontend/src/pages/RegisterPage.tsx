import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiClientError } from '../api/client'
import { useAuth } from '../context/AuthContext'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register(email, password)
      navigate('/')
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : 'Could not create account. Try a different email.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md glass-panel-strong p-8">
        <div className="mb-8 text-center">
          <h1 className="font-heading text-2xl font-semibold text-text">
            Create account
          </h1>
          <p className="text-sm text-muted mt-2 font-body">
            Set up access to your GEO analytics workspace
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm text-muted mb-1.5 font-body">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full glass-input px-3 py-2.5 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm text-muted mb-1.5 font-body">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full glass-input px-3 py-2.5 text-sm text-text focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
            />
          </div>

          {error && (
            <p className="text-sm text-coral font-body" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-md bg-accent text-bg text-sm font-medium font-body hover:bg-accent/90 disabled:opacity-60 transition-colors"
          >
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-sm text-muted text-center mt-6 font-body">
          Already have an account?{' '}
          <Link to="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
