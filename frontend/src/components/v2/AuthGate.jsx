import { useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api } from '../../api.js'

export default function AuthGate({ children }) {
  const location = useLocation()
  const [state, setState] = useState({ loading: true, user: null, error: '' })

  useEffect(() => {
    let active = true
    api.getAuthMe()
      .then((user) => active && setState({ loading: false, user, error: '' }))
      .catch((error) => active && setState({ loading: false, user: null, error: error.message }))
    return () => { active = false }
  }, [])

  if (state.loading) return <main className="auth-loading" aria-live="polite">正在确认登录状态…</main>
  if (!state.user) return <Navigate to="/login" replace state={{ from: location.pathname, error: state.error }} />
  return children
}
