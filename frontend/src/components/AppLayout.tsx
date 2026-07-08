import { Link, Outlet, useLocation } from 'react-router-dom'
import { Settings } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export function AppLayout() {
  const { user } = useAuth()
  const location = useLocation()
  const isAuthPage =
    location.pathname === '/login' || location.pathname === '/register'

  if (isAuthPage) {
    return <Outlet />
  }

  return (
    <div className="min-h-screen">
      <header className="glass-header sticky top-0 z-40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <Link
            to="/"
            className="font-heading text-lg font-semibold tracking-tight text-text hover:text-accent transition-colors"
          >
            AI GEO Copilot
          </Link>
          <nav className="flex items-center gap-4">
            {user && (
              <span className="text-sm text-muted hidden sm:inline font-body">
                {user.email}
              </span>
            )}
            <Link
              to="/settings"
              className="p-2 rounded-md text-muted hover:text-text hover:bg-white/5 transition-colors"
              aria-label="Settings"
            >
              <Settings size={18} />
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
