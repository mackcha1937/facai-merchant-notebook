import { useRef, useState } from 'react'
import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'
import AgentProposalCard from '../../components/v1/AgentProposalCard.jsx'
import { api } from '../../api.js'

let nextId = 1

export default function ChatHome() {
  const [messages, setMessages] = useState([
    { id: 0, role: 'assistant', kind: 'text', text: '下午好～直接告诉我客户今天买了什么、做了什么，写入前我会请你确认。' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setError('')
    setLoading(true)
    setMessages((prev) => [...prev, { id: nextId++, role: 'user', kind: 'text', text }])
    setInput('')
    try {
      const data = await api.interpret(text)
      if (data.error) {
        setMessages((prev) => [...prev, { id: nextId++, role: 'assistant', kind: 'error', text: data.error }])
      } else {
        setMessages((prev) => [...prev, { id: nextId++, role: 'assistant', kind: 'proposal', proposal: data }])
      }
    } catch (e) {
      setError(e.message)
      setMessages((prev) => [...prev, { id: nextId++, role: 'assistant', kind: 'error', text: e.message }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="v1-app">
      <AppHeader />
      <div className="v1-content v1-chat">
        <div className="v1-day">今天</div>
        {messages.map((m) => {
          if (m.kind === 'proposal') {
            return (
              <div key={m.id} className="v1-confirm-message">
                <AgentProposalCard proposal={m.proposal} />
              </div>
            )
          }
          if (m.kind === 'error') {
            return <div key={m.id} className="v1-message v1-assistant v1-msg-error">{m.text}</div>
          }
          return (
            <div key={m.id} className={`v1-message ${m.role === 'user' ? 'v1-user' : 'v1-assistant'}`}>
              {m.text}
            </div>
          )
        })}
        {loading && <div className="v1-message v1-assistant"><span className="v1-spinner" /> 正在解析…</div>}
        <div ref={bottomRef} />
      </div>

      {error && <div className="v1-error-banner" style={{ margin: '0 13px' }}>{error}</div>}

      <div className="v1-composer">
        <input
          placeholder="继续输入购买、核销或查询"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') send() }}
          disabled={loading}
        />
        <button className="v1-send" onClick={send} disabled={loading || !input.trim()}>➜</button>
      </div>
      <p className="v1-composer-hint">AI 可能理解有误，写入前会请你确认。</p>
      <BottomNavigation />
    </div>
  )
}
