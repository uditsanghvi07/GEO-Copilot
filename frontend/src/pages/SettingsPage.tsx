import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function SettingsPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-text mb-2">
          Settings
        </h1>
        <p className="text-sm text-muted font-body">
          Manage your account and workspace preferences
        </p>
      </div>

      <section className="glass-card p-6 space-y-4">
        <h2 className="font-heading text-base font-semibold">Account</h2>
        <div>
          <p className="text-xs text-muted font-body mb-1">Email</p>
          <p className="text-sm text-text font-body">{user?.email}</p>
        </div>
        <div>
          <p className="text-xs text-muted font-body mb-1">Session</p>
          <p className="text-sm text-muted font-body">
            Signed in with JWT. Token is stored locally for API requests.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="px-4 py-2 rounded-md hairline-border text-sm text-coral font-body hover:border-coral/40 transition-colors"
        >
          Sign out
        </button>
      </section>

      <section className="glass-card p-6 space-y-3">
        <h2 className="font-heading text-base font-semibold">API keys</h2>
        <p className="text-sm text-muted font-body leading-relaxed">
          API key management will be available in a future release. For now,
          authentication uses email and password via the backend JWT endpoints.
        </p>
        <div className="h-20 rounded-md border border-dashed border-border flex items-center justify-center">
          <span className="text-xs text-muted font-body">Placeholder for API key configuration</span>
        </div>
      </section>
    </div>
  )
}
