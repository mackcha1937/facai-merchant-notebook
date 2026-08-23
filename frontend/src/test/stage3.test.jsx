import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api } from '../api.js'
import ChatView from '../pages/v2/ChatView.jsx'
import AppShell from '../pages/v2/AppShell.jsx'
import CustomerRecordCard from '../components/v2/CustomerRecordCard.jsx'

const pendingProposal = {
  id: 7,
  status: 'pending',
  request_id: 'request-7',
  data_version: 1,
  title: '确认测试顾客甲的本次记账',
  changes_summary: '基础护理 1 次',
  absolute_date: '2026-08-21',
  precheck: '确认时重新检查权威数据',
  original_expression: '测试顾客甲昨天基础护理1次',
  actions: [{ type: 'consume_service', quantity: 1 }],
  customer: { customer_id: 1, display_name: '测试顾客甲' },
}

const messages = [
  { id: 1, session_date: '2026-08-21', role: 'owner', content: '前一日消息', message_type: 'text', blocks: [], read_at: null },
  { id: 2, session_date: '2026-08-22', role: 'assistant', content: '', message_type: 'block', read_at: null, blocks: [
    { id: 3, block_type: 'confirm_card', state: 'pending', data_version: 1, payload: pendingProposal },
  ] },
]

function mockConversation() {
  vi.spyOn(api, 'getChatHistory').mockResolvedValue({ messages, next_cursor: 1, has_more: true })
  vi.spyOn(api, 'getPendingActions').mockResolvedValue({ items: [{ id: 9, status: 'pending', read_at: null, proposal: pendingProposal }] })
  vi.spyOn(api, 'markMessageRead').mockResolvedValue({})
}

beforeEach(() => {
  window.localStorage.clear()
  window.sessionStorage.clear()
  vi.restoreAllMocks()
})

afterEach(() => vi.restoreAllMocks())

describe('阶段3真实聊天恢复', () => {
  it('刷新后恢复历史、跨日分隔、未完成卡和游标入口', async () => {
    mockConversation()
    render(<ChatView draftInput="" onDraftChange={() => {}} />)
    expect(await screen.findByText('确认测试顾客甲的本次记账')).toBeInTheDocument()
    expect(screen.getAllByTestId('date-separator')).toHaveLength(2)
    expect(screen.getByText(/有 1 项未完成确认/)).toBeInTheDocument()
    expect(screen.getByText('加载更早消息')).toBeInTheDocument()
    expect(screen.getAllByText('2026-08-21')).toHaveLength(2)
  })

  it('手机/Web 冲突在原卡片显示可恢复回执', async () => {
    mockConversation()
    vi.spyOn(api, 'confirmStage3Proposal').mockRejectedValue(Object.assign(new Error('该确认卡已由另一设备处理'), {
      status: 409,
      payload: { status: 'conflict', recoverable: true, original_result: { results: [{ message: '已写入一次' }] } },
    }))
    render(<ChatView draftInput="" onDraftChange={() => {}} />)
    fireEvent.click(await screen.findByText('确认'))
    expect(await screen.findByText('确认冲突')).toBeInTheDocument()
    expect(screen.getByText(/另一设备处理/)).toBeInTheDocument()
    expect(api.confirmStage3Proposal).toHaveBeenCalledTimes(1)
  })

  it('网络失败保留输入草稿并可原位重试', async () => {
    vi.spyOn(api, 'getChatHistory').mockResolvedValue({ messages: [], next_cursor: null, has_more: false })
    vi.spyOn(api, 'getPendingActions').mockResolvedValue({ items: [] })
    vi.spyOn(api, 'streamChatTurn').mockRejectedValue(new Error('网络不可用'))

    function Harness() {
      const [draft, setDraft] = useState('测试顾客甲基础护理1次')
      return <ChatView draftInput={draft} onDraftChange={setDraft} />
    }
    render(<Harness />)
    await screen.findByText(/你好，记账时请写明/)
    fireEvent.click(screen.getByLabelText('发送'))
    expect(await screen.findByText(/输入草稿已保留/)).toBeInTheDocument()
    expect(screen.getByDisplayValue('测试顾客甲基础护理1次')).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
  })
})

describe('权威历史卡与 ContextStack', () => {
  it('真实客户档案显示后端 data_version 和派生余额', () => {
    render(<CustomerRecordCard record={{
      id: 1, display_name: '测试顾客甲', aliases: [], authoritative: true, data_version: 12,
      service_type_count: 1, active_package_count: 1,
      services: [{ service_id: 2, service_name: '基础护理', last_consumed_at: '2026-08-21', total_remaining_count: 4 }],
      recent_entries: [],
    }} onBackToList={() => {}} onOpenService={() => {}} />)
    expect(screen.getByText('权威 #12')).toBeInTheDocument()
    fireEvent.click(screen.getByText('服务套餐'))
    expect(screen.getByText(/剩4次/)).toBeInTheDocument()
  })

  it('刷新恢复深层 ContextStack，浏览器返回回到同一根对话', async () => {
    window.sessionStorage.setItem('facai-v2-context-stack', JSON.stringify([
      { viewType: 'chat', originType: 'chat', scrollPosition: 0, draftInput: '保留草稿' },
      { viewType: 'customer_index', originType: 'chat', query: '', filters: {}, filter: 'all', sort: 'recent', scrollPosition: 0 },
    ]))
    window.localStorage.setItem('facai-v2-draft', '保留草稿')
    vi.spyOn(api, 'getCustomers').mockResolvedValue([])
    vi.spyOn(api, 'getProducts').mockResolvedValue([])
    vi.spyOn(api, 'getChatHistory').mockResolvedValue({ messages: [], next_cursor: null, has_more: false })
    vi.spyOn(api, 'getPendingActions').mockResolvedValue({ items: [] })
    render(<AppShell initialView="chat" />)
    expect(await screen.findByTestId('right-workspace')).toBeInTheDocument()
    expect(screen.getByDisplayValue('保留草稿')).toBeInTheDocument()
    window.dispatchEvent(new PopStateEvent('popstate', { state: { v2app: true, ctxDepth: 0 } }))
    await waitFor(() => expect(screen.queryByTestId('right-workspace')).not.toBeInTheDocument())
    expect(screen.getByTestId('chat-view')).toBeInTheDocument()
  })
})
