import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { api } from '../api.js'
import ConfirmCard from '../components/v2/ConfirmCard.jsx'
import CustomerRecordCard from '../components/v2/CustomerRecordCard.jsx'
import ManageDetailView from '../components/v2/ManageDetailView.jsx'
import ChatView from '../pages/v2/ChatView.jsx'
import VerifyV2Stage4 from '../pages/v2/VerifyV2Stage4.jsx'

const factProductProposal = {
  id: 41,
  status: 'pending',
  data_version: 2,
  title: '确认甲姐的客户事实和业务记录',
  changes_summary: '敏感事实：敏感；购买星云修护霜 2件',
  absolute_date: '2026-08-23',
  original_expression: '甲姐皮肤敏感，今天买了星云修护霜2瓶',
  actions: [
    {
      type: 'upsert_customer_fact', fact_type: 'skin_condition', display_value: '敏感',
      evidence_text: '甲姐皮肤敏感，今天买了星云修护霜2瓶', confidence: 0.94,
      sensitivity_level: 'sensitive',
    },
    {
      type: 'record_product_purchase', canonical_name: '星云修护霜', product_name: '星云修护霜',
      create_product: true, quantity: 2,
    },
  ],
}

beforeEach(() => vi.restoreAllMocks())

describe('阶段4确认卡', () => {
  it('敏感事实单列、保留证据并可在最终确认前移除', async () => {
    const onEdit = vi.fn().mockResolvedValue({})
    render(<ConfirmCard proposal={factProductProposal} real onEdit={onEdit} onConfirm={() => {}} onCancel={() => {}} />)
    expect(screen.getByText(/敏感\/不适事实/)).toBeInTheDocument()
    expect(screen.getByText(/证据：甲姐皮肤敏感/)).toBeInTheDocument()
    expect(screen.getByText(/新增草稿\/资料待补充/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('修改'))
    fireEvent.click(screen.getByLabelText('保留此事实'))
    fireEvent.click(screen.getByText('保存修改'))
    await waitFor(() => expect(onEdit).toHaveBeenCalled())
    expect(onEdit.mock.calls[0][0].removeActionIndexes).toEqual([0])
    expect(onEdit.mock.calls[0][0].quantityActionIndex).toBe(1)
  })

  it('客户档案展示已确认事实和产品知识状态', () => {
    render(<CustomerRecordCard record={{
      id: 1, display_name: '甲姐', aliases: [], authoritative: true, data_version: 1001,
      services: [], recent_entries: [],
      facts: [{ id: 3, type: 'skin_condition', value: '敏感', confirmed: true }],
      products: [{ id: 5, name: '星云修护霜', last_purchased_at: '2026-08-23', purchase_count: 1, knowledge_status: 'incomplete' }],
    }} onBackToList={() => {}} />)
    fireEvent.click(screen.getByText('客户事实'))
    expect(screen.getByText('敏感')).toBeInTheDocument()
    fireEvent.click(screen.getByText('产品'))
    expect(screen.getByText('星云修护霜')).toBeInTheDocument()
  })
})

describe('阶段4产品管理与聊天匹配', () => {
  it('产品管理只生成新增 Proposal', async () => {
    const onCreate = vi.fn().mockResolvedValue({})
    render(<ManageDetailView group={{ id: 'products_services' }} products={[]} onBack={() => {}} onCreateProduct={onCreate} />)
    fireEvent.change(screen.getByLabelText('标准名称'), { target: { value: '新产品霜' } })
    fireEvent.click(screen.getByText('生成新增确认卡'))
    await waitFor(() => expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ canonical_name: '新产品霜' })))
    expect(screen.getByText(/不会在本页直接写入/)).toBeInTheDocument()
  })

  it('产品候选选择调用解析接口后刷新为最终确认卡', async () => {
    const resolving = {
      id: 51, status: 'resolving', data_version: 1,
      product_match: {
        status: 'ambiguous', recognized: { name: '舒缓修复面膜' },
        candidates: [
          { id: 8, name: '舒缓修护面膜', brand: '品牌A', spec: '5片', score: 0.82, match_method: 'fuzzy' },
        ],
      },
    }
    vi.spyOn(api, 'getChatHistory')
      .mockResolvedValueOnce({ messages: [{
        id: 1, session_date: '2026-08-23', role: 'assistant', content: '', message_type: 'block', read_at: null,
        blocks: [{ id: 2, block_type: 'product_match_card', state: 'resolving', data_version: 1, payload: resolving }],
      }], next_cursor: null, has_more: false })
      .mockResolvedValue({ messages: [], next_cursor: null, has_more: false })
    vi.spyOn(api, 'getPendingActions').mockResolvedValue({ items: [] })
    vi.spyOn(api, 'markMessageRead').mockResolvedValue({})
    vi.spyOn(api, 'resolveProposalProduct').mockResolvedValue({ status: 'pending' })
    render(<ChatView draftInput="" onDraftChange={() => {}} />)
    fireEvent.click(await screen.findByText('舒缓修护面膜'))
    await waitFor(() => expect(api.resolveProposalProduct).toHaveBeenCalledWith(51, expect.objectContaining({ product_id: 8, create_new: false })))
  })
})

describe('阶段4真实模型静态验收状态', () => {
  it('展示隔离验收通过和累计次数，同时保持常驻模型未生效', async () => {
    vi.spyOn(api, 'getStage4Status').mockResolvedValue({
      capabilities: {},
      model_validation: {
        configured: true,
        enabled: false,
        effective: false,
        isolated_validation: 'passed',
        total_paid_calls: 2,
      },
      test_results: { status: '通过' },
    })
    vi.spyOn(api, 'getProducts').mockResolvedValue([])

    render(<MemoryRouter><VerifyV2Stage4 /></MemoryRouter>)

    expect(await screen.findByText('已通过')).toBeInTheDocument()
    expect(screen.getByText('2 次（静态验收记录）')).toBeInTheDocument()
    expect(screen.getByText('未生效（保持关闭）')).toBeInTheDocument()
    expect(screen.queryByText(/等待授权|未执行/)).not.toBeInTheDocument()
  })
})
