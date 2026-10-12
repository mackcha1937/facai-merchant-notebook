import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../../api.js'

export default function LoginPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ invite_code: '', display_name: '', login_name: '', password: '' })
  const [error, setError] = useState(location.state?.error || '')
  const [busy, setBusy] = useState(false)
  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'invite') await api.redeemInvite(form)
      else await api.login({ login_name: form.login_name, password: form.password })
      navigate(location.state?.from || '/app/chat', { replace: true })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <Link className="auth-brand" to="/" aria-label="返回发财产品首页"><span>发</span><strong>发财</strong></Link>
        <p className="auth-eyebrow">邀请内测</p>
        <h1 id="auth-title">{mode === 'invite' ? '开通店铺账号' : '登录店主工作台'}</h1>
        <p className="auth-intro">{mode === 'invite' ? '使用我们单独发给你的一次性邀请码。' : '顾客资料会按店铺隔离，只对已邀请的店主开放。'}</p>
        <div className="auth-tabs" role="tablist" aria-label="登录方式">
          <button type="button" role="tab" aria-selected={mode === 'login'} onClick={() => { setMode('login'); setError('') }}>已有账号</button>
          <button type="button" role="tab" aria-selected={mode === 'invite'} onClick={() => { setMode('invite'); setError('') }}>首次开通</button>
        </div>
        <form onSubmit={submit}>
          {mode === 'invite' && <>
            <label>邀请码<input autoComplete="one-time-code" value={form.invite_code} onChange={update('invite_code')} required minLength="8" /></label>
            <label>店主称呼<input autoComplete="name" value={form.display_name} onChange={update('display_name')} required maxLength="100" /></label>
          </>}
          <label>登录名<input autoComplete="username" value={form.login_name} onChange={update('login_name')} required minLength="3" /></label>
          <label>密码<input type="password" autoComplete={mode === 'invite' ? 'new-password' : 'current-password'} value={form.password} onChange={update('password')} required minLength={mode === 'invite' ? 10 : 1} /></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" disabled={busy}>{busy ? '正在处理…' : (mode === 'invite' ? '开通并进入工作台' : '登录')}</button>
        </form>
        <p className="auth-security">我们不会在前端显示API Key。账本变更仍需店主确认。</p>
      </section>
    </main>
  )
}
