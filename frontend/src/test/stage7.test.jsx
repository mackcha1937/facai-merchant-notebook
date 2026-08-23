import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api.js'
import AdminEvaluations from '../pages/v2/AdminEvaluations.jsx'
import VerifyV2Stage7 from '../pages/v2/VerifyV2Stage7.jsx'

const emptyReleases = { prompt: [], rag: [], recommendation: [] }

beforeEach(() => vi.restoreAllMocks())

function mockLists({ drafts = [], runs = [], releases = emptyReleases, audits = [] } = {}) {
  vi.spyOn(api, 'getEvaluationDrafts').mockResolvedValue(drafts)
  vi.spyOn(api, 'getEvaluationRuns').mockResolvedValue(runs)
  vi.spyOn(api, 'getEvaluationReleases').mockResolvedValue(releases)
  vi.spyOn(api, 'getEvaluationAudits').mockResolvedValue(audits)
}

describe('阶段7管理员测评台', () => {
  it('明确显示阻塞门禁、CSV往返且不能强行发布', async () => {
    mockLists({
      drafts: [{ id: 1, config_type: 'recommendation', status: 'blocked', data_version: 1, checksum: 'abcdef123456' }],
      runs: [{ id: 2, draft_id: 1, summary: { gate_status: 'blocked', release_allowed: false, passed: 0, total: 60, failed: 0, blocked: 60, safety_passed: 0, safety_total: 49, manual_averages: {} } }],
    })
    vi.spyOn(api, 'startEvaluationRun').mockResolvedValue({})
    render(<MemoryRouter><AdminEvaluations /></MemoryRouter>)
    expect(await screen.findByText(/Run #2 · blocked/)).toBeInTheDocument()
    expect(screen.getByText(/通过 0\/60/)).toBeInTheDocument()
    expect(screen.getByText(/未真实执行的用例绝不记为通过/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '导出CSV工作簿' })).toHaveAttribute('href', '/api/admin/evaluations/runs/2/workbook.csv')
    expect(screen.getByRole('button', { name: '发布已测评版本' })).toBeDisabled()
    fireEvent.click(screen.getByText('运行离线测评'))
    await waitFor(() => expect(api.startEvaluationRun).toHaveBeenCalledWith(expect.objectContaining({
      draft_id: 1, idempotency_key: expect.stringMatching(/^stage7-run-1-/),
    })))
  })

  it('门槛通过后要求精确确认并携带版本与幂等信息发布', async () => {
    mockLists({
      drafts: [{ id: 3, config_type: 'prompt', status: 'evaluated', data_version: 4, checksum: '12345678abcdef' }],
      runs: [{ id: 9, draft_id: 3, summary: { gate_status: 'passed', release_allowed: true, passed: 60, total: 60, failed: 0, blocked: 0, safety_passed: 49, safety_total: 49, manual_averages: { factual: 5, safety: 5, natural: 4.5, interaction: 5 } } }],
    })
    vi.spyOn(api, 'publishEvaluationRelease').mockResolvedValue({ release_id: 1 })
    render(<MemoryRouter><AdminEvaluations /></MemoryRouter>)
    const confirmation = await screen.findByLabelText('Run 9 发布确认')
    const publish = screen.getByRole('button', { name: '发布已测评版本' })
    expect(publish).toBeDisabled()
    fireEvent.change(confirmation, { target: { value: 'PUBLISH-3-12345678' } })
    expect(publish).toBeEnabled()
    fireEvent.click(publish)
    await waitFor(() => expect(api.publishEvaluationRelease).toHaveBeenCalledWith(expect.objectContaining({
      draft_id: 3,
      run_id: 9,
      confirmation: 'PUBLISH-3-12345678',
      expected_data_version: 4,
      request_id: expect.stringMatching(/^stage7-publish-9-request-/),
      idempotency_key: expect.stringMatching(/^stage7-publish-9-/),
    })))
  })

  it('只对当前发布版本开放精确二次确认回滚并展示审计', async () => {
    mockLists({
      releases: { prompt: [{ id: 7, version: 2, status: 'published', evaluation_run_id: 9, rollback_confirmation: 'ROLLBACK-prompt-7' }], rag: [], recommendation: [] },
      audits: [{ id: 1, release_type: 'prompt', action: 'publish', release_id: 7, created_at: '2026-08-23T10:00:00' }],
    })
    vi.spyOn(api, 'rollbackEvaluationRelease').mockResolvedValue({ restored_version: 1 })
    render(<MemoryRouter><AdminEvaluations /></MemoryRouter>)
    expect(await screen.findByText(/prompt · publish/)).toBeInTheDocument()
    const confirmation = screen.getByLabelText('prompt 7 回滚确认')
    fireEvent.change(confirmation, { target: { value: 'ROLLBACK-prompt-7' } })
    fireEvent.click(screen.getByRole('button', { name: '回滚上一版本' }))
    await waitFor(() => expect(api.rollbackEvaluationRelease).toHaveBeenCalledWith(expect.objectContaining({
      release_type: 'prompt', release_id: 7, confirmation: 'ROLLBACK-prompt-7',
    })))
  })
})

describe('/verify/v2-stage-7', () => {
  it('展示离线能力、自动执行器边界、零真实模型与未公开部署', async () => {
    vi.spyOn(api, 'getStage7Status').mockResolvedValue({ capabilities: { jsonl_manifest_runner: true, automatic_runtime_executor: false, manual_csv_roundtrip: true, safety_gate: true, quality_score_gate: true, two_step_publish: true, rollback: true } })
    render(<MemoryRouter><VerifyV2Stage7 /></MemoryRouter>)
    expect(await screen.findByText('jsonl_manifest_runner')).toBeInTheDocument()
    expect(screen.getByText('automatic_runtime_executor')).toBeInTheDocument()
    expect(screen.getByText('0 / 0')).toBeInTheDocument()
    expect(screen.getByText('未开始')).toBeInTheDocument()
  })
})
