import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api.js'
import AuthGate from '../components/v2/AuthGate.jsx'
import LoginPage from '../pages/v2/LoginPage.jsx'

afterEach(() => {
  vi.restoreAllMocks()
  document.cookie = 'facai_csrf=; Max-Age=0; path=/'
})

describe('邀请内测认证界面', () => {
  it('未登录访问业务页会跳转登录，不渲染受保护内容', async () => {
    vi.spyOn(api, 'getAuthMe').mockRejectedValue(Object.assign(new Error('请先登录'), { status: 401 }))
    render(
      <MemoryRouter initialEntries={['/app/chat']}>
        <Routes>
          <Route path="/app/chat" element={<AuthGate><p>私密账本</p></AuthGate>} />
          <Route path="/login" element={<p>登录入口</p>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByText('登录入口')).toBeInTheDocument()
    expect(screen.queryByText('私密账本')).not.toBeInTheDocument()
  })

  it('有效会话才展示受保护内容', async () => {
    vi.spyOn(api, 'getAuthMe').mockResolvedValue({ user_id: 7, tenant_id: 2, role: 'owner' })
    render(<MemoryRouter><AuthGate><p>私密账本</p></AuthGate></MemoryRouter>)
    expect(await screen.findByText('私密账本')).toBeInTheDocument()
  })

  it('首次开通提交一次性邀请码，成功后进入工作台', async () => {
    const redeem = vi.spyOn(api, 'redeemInvite').mockResolvedValue({ user_id: 7, tenant_id: 2 })
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app/chat" element={<p>店主工作台</p>} />
        </Routes>
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByRole('tab', { name: '首次开通' }))
    fireEvent.change(screen.getByLabelText('邀请码'), { target: { value: 'FC-AAAA-BBBB-CCCC' } })
    fireEvent.change(screen.getByLabelText('店主称呼'), { target: { value: '星澜店主' } })
    fireEvent.change(screen.getByLabelText('登录名'), { target: { value: 'xinglan_owner' } })
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'safe-password-123' } })
    fireEvent.click(screen.getByRole('button', { name: '开通并进入工作台' }))

    await waitFor(() => expect(redeem).toHaveBeenCalledWith({
      invite_code: 'FC-AAAA-BBBB-CCCC',
      display_name: '星澜店主',
      login_name: 'xinglan_owner',
      password: 'safe-password-123',
    }))
    expect(await screen.findByText('店主工作台')).toBeInTheDocument()
  })
})

describe('浏览器认证请求契约', () => {
  it('写请求携带同源 Cookie 和双提交 CSRF 请求头', async () => {
    document.cookie = 'facai_csrf=csrf-test-token; path=/'
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ authenticated: true }),
    })
    await api.login({ login_name: 'owner', password: 'password' })
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
      method: 'POST',
      credentials: 'same-origin',
      headers: expect.objectContaining({ 'X-CSRF-Token': 'csrf-test-token' }),
    }))
  })
})
