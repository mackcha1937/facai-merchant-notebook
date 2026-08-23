import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { api } from '../api.js'
import RecommendationTodayTaskCard from '../components/v2/RecommendationTodayTaskCard.jsx'
import { resolveRecommendationSnooze } from '../pages/v2/AppShell.jsx'
import VerifyV2Stage6 from '../pages/v2/VerifyV2Stage6.jsx'

const recommendation = {
  id: 12, type: 'product_repurchase',
  customer: { id: 3, display_name: '虚构顾客星澜' },
  subject: { type: 'product', id: 8, name: '星河面霜' },
  reason: '距最近一次购买已 70 天，达到规则 60 天',
  suggested_action: '先询问近期使用感受，再按客户需要回应',
  score: 75, score_breakdown: { base: 50 }, policy_version: 'stage6-sql-v1', rule_version: 1,
  status: 'new', unread: true, read_at: null, handled_at: null, snoozed_until: null,
  data_version: 1, degraded: false, degraded_reason: null,
  evidence: [
    { kind: 'transaction', entry_id: 7, occurred_on: '2026-06-01', quantity: 1, source: 'tenant_sql' },
    { document_id: 5, knowledge_version: 1, source: { name: '虚构确认资料' }, score: 1 },
  ],
  message_drafts: [{ id: 21, variant: 'standard', content: '星澜，最近星河面霜用着还顺手吗？需要时和我说就好。', data_version: 1 }],
  external_send_available: false,
}
const task = {
  id: 'recommendation-12', recommendation_id: 12, group: 'suggested_follow_up',
  customer_name: recommendation.customer.display_name, summary: recommendation.reason,
  date: '今日', unread: true, read_at: null, handled_at: null,
  status: 'new', data_version: 1, recommendation,
}

describe('阶段6今日事项交互', () => {
  it('打开列表不批量清零，逐条打开才read；复制和状态动作分离', async () => {
    const onRead = vi.fn()
    const onCopy = vi.fn().mockResolvedValue()
    const onAction = vi.fn().mockResolvedValue()
    render(<RecommendationTodayTaskCard tasks={[task]} groupLabels={{ suggested_follow_up: '建议跟进' }} onRead={onRead} onCopy={onCopy} onRecommendationAction={onAction} />)
    expect(screen.getByText('未处理 1 · 未查看 1')).toBeInTheDocument()
    expect(onRead).not.toHaveBeenCalled()
    fireEvent.click(screen.getByLabelText(/虚构顾客星澜/))
    expect(onRead).toHaveBeenCalledWith(task.id, task)
    expect(screen.getByText(/账本购买/)).toBeInTheDocument()
    expect(screen.getByText(/证据链完整/)).toBeInTheDocument()
    expect(screen.queryByText(/发送微信|发送短信|立即发送/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('复制话术'))
    await waitFor(() => expect(onCopy).toHaveBeenCalled())
    expect(onAction).not.toHaveBeenCalled()
    fireEvent.change(screen.getByPlaceholderText(/客户说偏好清爽/), { target: { value: '客户说偏好清爽，10天后再问' } })
    fireEvent.click(screen.getByText('已联系'))
    await waitFor(() => expect(onAction).toHaveBeenCalledWith(task, 'contacted', '客户说偏好清爽，10天后再问', ''))
  })

  it('提供确定性短一点与不提购买改写，不出现规则权重或发送控件', () => {
    const onRewrite = vi.fn().mockResolvedValue()
    render(<RecommendationTodayTaskCard tasks={[task]} groupLabels={{ suggested_follow_up: '建议跟进' }} onRewrite={onRewrite} />)
    fireEvent.click(screen.getByLabelText(/虚构顾客星澜/))
    fireEvent.click(screen.getByText('短一点'))
    fireEvent.click(screen.getByText('不提购买'))
    expect(onRewrite).toHaveBeenCalledWith(task, 'shorter')
    expect(onRewrite).toHaveBeenCalledWith(task, 'no_purchase')
    expect(screen.queryByText(/overdue_per_day|cooldown_days|API Key/)).not.toBeInTheDocument()
  })

  it('含日期的稍后反馈只进入待确认，并要求AI不准确说明', async () => {
    const onAction = vi.fn().mockResolvedValue({ proposal: { id: 99 } })
    render(<RecommendationTodayTaskCard tasks={[task]} groupLabels={{ suggested_follow_up: '建议跟进' }} onRecommendationAction={onAction} />)
    fireEvent.click(screen.getByLabelText(/虚构顾客星澜/))
    fireEvent.change(screen.getByPlaceholderText(/客户说偏好清爽/), { target: { value: '10天后再问' } })
    fireEvent.click(screen.getByText('稍后'))
    await waitFor(() => expect(onAction).toHaveBeenCalledWith(task, 'snoozed', '10天后再问', ''))
    expect(await screen.findByText(/已生成待确认事项/)).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText(/客户说偏好清爽/), { target: { value: '' } })
    fireEvent.click(screen.getByText('AI不准确'))
    expect(await screen.findByText(/请先填写AI不准确/)).toBeInTheDocument()
    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('稍后时间解析不会用默认时间绕过原文日期确认', () => {
    expect(resolveRecommendationSnooze('snoozed', '客户说10天后再问', '2026-08-24T10:00')).toBeNull()
    expect(resolveRecommendationSnooze('snoozed', '请在2026-09-03联系', '')).toBeNull()
    expect(resolveRecommendationSnooze('contacted', '', '2026-08-24T10:00')).toBeNull()
    expect(resolveRecommendationSnooze('snoozed', '', '2026-08-24T10:00')).toBe(new Date('2026-08-24T10:00').toISOString())
  })
})

describe('/verify/v2-stage-6', () => {
  it('只读展示阶段6边界、Top3与零外部调用', async () => {
    vi.spyOn(api, 'getStage6Status').mockResolvedValue({
      migration: '0019_stage6_recommendation_feedback',
      capabilities: Object.fromEntries([
        'sql_authoritative_rules', 'hard_exclusions_before_score', 'top3_unique_customers',
        'stable_rag_snapshot', 'deterministic_safe_templates', 'copy_only_no_send',
        'read_and_handled_separate', 'feedback_proposal_confirmation',
      ].map((key) => [key, true])),
      test_results: { status: '通过', backend: '270 passed', frontend: '待复跑', build: '待复跑' },
    })
    vi.spyOn(api, 'getTodayRecommendations').mockResolvedValue({ unresolved_count: 1, unread_count: 1, items: [recommendation] })
    render(<MemoryRouter><VerifyV2Stage6 /></MemoryRouter>)
    expect(await screen.findByText(/SQL 权威事实先执行硬排除/)).toBeInTheDocument()
    expect(screen.getByText(/未处理 1 · 未查看 1/)).toBeInTheDocument()
    expect(screen.getByText('0 / 0 / 0')).toBeInTheDocument()
    expect(screen.getByText('未开始')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })
})
