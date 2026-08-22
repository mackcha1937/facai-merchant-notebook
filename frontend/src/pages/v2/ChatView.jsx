// 对话主界面：日期分隔、店主消息、AI文本、各类固定 UI Block、加载/空/失败/重试/取消示例。
// 使用 Mock 数据，不接真实 AI；AI 不返回任意 HTML，所有卡片由固定组件渲染。
import { useEffect, useRef, useState } from 'react'
import ChatComposer from '../../components/v2/ChatComposer.jsx'
import ConfirmCard from '../../components/v2/ConfirmCard.jsx'
import CustomerRecordCard from '../../components/v2/CustomerRecordCard.jsx'
import ProductMatchCard from '../../components/v2/ProductMatchCard.jsx'
import ReceiptCard from '../../components/v2/ReceiptCard.jsx'
import TodayTaskCard from '../../components/v2/TodayTaskCard.jsx'
import CustomerIndexCard from '../../components/v2/CustomerIndexCard.jsx'
import { mockChatMessages, mockCustomerRecord, mockCustomers, mockProductMatches, mockTodayTasks, todayTaskGroups } from '../../fixtures/mock/index.js'

const MOCK_PROPOSAL = {
  id: 'demo-proposal',
  title: '确认阿珍今天的面部清洁与商品购买',
  changes_summary: '面部清洁 1 次 + 购买舒缓保湿霜 1 件',
  absolute_date: '2026-08-22',
  precheck: '余额充足，无冲突',
  original_expression: '阿珍今天面部清洁1次，还买了舒缓保湿霜',
  quantity: 1,
}

export default function ChatView({ draftInput, onDraftChange, sending, onSend, onStop }) {
  const [messages, setMessages] = useState(() => [
    { id: 'd0', kind: 'date', text: '今天' },
    { id: 'm0', kind: 'ai-text', text: '下午好～今天想记点什么？' },
    { id: 'm1', kind: 'owner', text: '阿珍今天面部清洁1次，还买了舒缓保湿霜' },
    { id: 'm2', kind: 'confirm', proposal: MOCK_PROPOSAL },
    { id: 'm3', kind: 'receipt', status: 'success', title: '已确认（Mock）', detail: '阶段2演示数据，未写入真实账本', result: ['面部清洁 1 次', '购买舒缓保湿霜 1 件'] },
    { id: 'm4', kind: 'product', match: mockProductMatches.ambiguous },
    { id: 'm5', kind: 'customer-record', record: mockCustomerRecord },
    { id: 'm6', kind: 'customer-index', customers: mockCustomers },
    { id: 'm7', kind: 'today', tasks: mockTodayTasks, groupLabels: todayTaskGroups },
    { id: 'm8', kind: 'failure', text: '（示例）网络失败：请检查连接后重试' },
  ])
  const bottomRef = useRef(null)
  const listRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  const submit = () => {
    const text = draftInput.trim()
    if (!text || sending) return
    onDraftChange('')
    onSend?.(text)
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, kind: 'owner', text },
      { id: `c-${Date.now()}`, kind: 'confirm', proposal: { ...MOCK_PROPOSAL, original_expression: text } },
    ])
  }

  const renderMessage = (m) => {
    switch (m.kind) {
      case 'date':
        return <div key={m.id} className="v2-day">{m.text}</div>
      case 'owner':
        return <div key={m.id} className="v2-msg owner">{m.text}</div>
      case 'ai-text':
        return <div key={m.id} className="v2-msg assistant">{m.text}</div>
      case 'confirm':
        return (
          <div key={m.id} className="v2-msg-block">
            <ConfirmCard proposal={m.proposal} onConfirm={() => {}} onCancel={() => {}} />
          </div>
        )
      case 'receipt':
        return (
          <div key={m.id} className="v2-msg-block">
            <ReceiptCard status={m.status} title={m.title} detail={m.detail} result={m.result} />
          </div>
        )
      case 'product':
        return (
          <div key={m.id} className="v2-msg-block">
            <ProductMatchCard match={m.match} onChoose={() => {}} onAddNew={() => {}} />
          </div>
        )
      case 'customer-record':
        return (
          <div key={m.id} className="v2-msg-block">
            <CustomerRecordCard record={m.record} onBackToList={() => {}} onOpenService={() => {}} />
          </div>
        )
      case 'customer-index':
        return (
          <div key={m.id} className="v2-msg-block">
            <CustomerIndexCard customers={m.customers} onOpenCustomer={() => {}} onBack={() => {}} />
          </div>
        )
      case 'today':
        return (
          <div key={m.id} className="v2-msg-block">
            <TodayTaskCard tasks={m.tasks} groupLabels={m.groupLabels} onRead={() => {}} onHandle={() => {}} onBack={() => {}} />
          </div>
        )
      case 'failure':
        return (
          <div key={m.id} className="v2-msg-block">
            <ReceiptCard status="failure" title="网络失败" detail={m.text} onRetry={() => {}} />
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="v2-chat" data-testid="chat-view">
      <div className="v2-chat-scroll" ref={listRef}>
        {messages.map(renderMessage)}
        {sending && <div className="v2-msg assistant"><span className="v2-spinner" /> 正在生成…（可停止）</div>}
        <div ref={bottomRef} />
      </div>
      <ChatComposer input={draftInput} onInputChange={onDraftChange} onSend={submit} sending={sending} onStop={onStop} />
    </div>
  )
}
