import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api.js'
import VerifyV2Stage8 from '../pages/v2/VerifyV2Stage8.jsx'


afterEach(() => vi.restoreAllMocks())

describe('/verify/v2-stage-8', () => {
  it('展示本地总验收能力、数据库完整性和明确未上线边界', async () => {
    vi.spyOn(api, 'getStage8Status').mockResolvedValue({
      stage: 8,
      database: { migration: '0021_pilot_auth_production', integrity: 'ok', foreign_key_errors: 0 },
      capabilities: {
        stage1_to_7_regression: true,
        multi_day_and_cross_device: true,
        network_failure_recovery: true,
        model_and_index_degrade: true,
        backup_restore_rehearsal: true,
        responsive_desktop_mobile: true,
        security_headers: true,
        accessibility_baseline: true,
      },
      runtime_boundaries: {
        real_model_effective: false,
        external_embedding: false,
        external_message_send: false,
        production_authentication: true,
        public_deployment: false,
      },
    })
    render(<MemoryRouter><VerifyV2Stage8 /></MemoryRouter>)
    expect(await screen.findByText('0021_pilot_auth_production')).toBeInTheDocument()
    expect(screen.getByText('multi_day_and_cross_device')).toBeInTheDocument()
    expect(screen.getByText('0 / 0')).toBeInTheDocument()
    expect(screen.getByText('生产认证').nextSibling).toHaveTextContent('已完成')
    expect(screen.getByText('公开部署').nextSibling).toHaveTextContent('未开始')
    expect(document.body.textContent).not.toMatch(/DEEPSEEK_API_KEY|sk-[A-Za-z0-9]{8,}/i)
  })

  it('接口失败时保留原页面并显示可理解错误', async () => {
    vi.spyOn(api, 'getStage8Status').mockRejectedValue(new Error('本地验收报告暂不可用'))
    render(<MemoryRouter><VerifyV2Stage8 /></MemoryRouter>)
    expect(await screen.findByRole('alert')).toHaveTextContent('本地验收报告暂不可用')
    expect(screen.getByRole('heading', { name: /阶段8本地总验收/ })).toBeInTheDocument()
  })
})
