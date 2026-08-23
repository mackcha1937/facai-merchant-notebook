import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../../api.js'
import ChatComposer from '../../components/v2/ChatComposer.jsx'
import ConfirmCard from '../../components/v2/ConfirmCard.jsx'
import ReceiptCard from '../../components/v2/ReceiptCard.jsx'
import ProductMatchCard from '../../components/v2/ProductMatchCard.jsx'

function uniqueId(prefix) {
  const random = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `${prefix}-${random}`
}

function getDeviceId() {
  const key = 'facai-v2-device-id'
  let value = window.localStorage.getItem(key)
  if (!value) {
    value = uniqueId('device')
    window.localStorage.setItem(key, value)
  }
  return value
}

function dayLabel(value) {
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
  return value === today ? '今天' : value
}

export default function ChatView({ draftInput, onDraftChange, onAuthoritativeWrite, onPendingChange, refreshToken = 0 }) {
  const [messages, setMessages] = useState([])
  const [pending, setPending] = useState([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [streamText, setStreamText] = useState('')
  const [error, setError] = useState('')
  const [cursor, setCursor] = useState(null)
  const [hasMore, setHasMore] = useState(false)
  const bottomRef = useRef(null)
  const confirmKeys = useRef(new Map())
  const deviceId = useMemo(getDeviceId, [])

  const refresh = useCallback(async ({ scroll = true } = {}) => {
    const [history, pendingResult] = await Promise.all([
      api.getChatHistory({ limit: 40 }),
      api.getPendingActions(),
    ])
    setMessages(history.messages)
    setCursor(history.next_cursor)
    setHasMore(history.has_more)
    setPending(pendingResult.items || [])
    onPendingChange?.(pendingResult.items || [])
    setLoading(false)
    setError('')
    history.messages.filter((m) => m.role === 'assistant' && !m.read_at).forEach((m) => {
      api.markMessageRead(m.id).catch(() => {})
    })
    if (scroll) window.requestAnimationFrame(() => {
      if (typeof bottomRef.current?.scrollIntoView === 'function') bottomRef.current.scrollIntoView({ block: 'end' })
    })
  }, [onPendingChange])

  useEffect(() => {
    refresh().catch((failure) => {
      setLoading(false)
      setError(failure.message)
    })
  }, [refresh, refreshToken])

  const loadEarlier = async () => {
    if (!cursor) return
    try {
      const history = await api.getChatHistory({ before: cursor, limit: 40 })
      setMessages((current) => [...history.messages, ...current])
      setCursor(history.next_cursor)
      setHasMore(history.has_more)
    } catch (failure) {
      setError(failure.message)
    }
  }

  const submit = async () => {
    const text = draftInput.trim()
    if (!text || sending) return
    setSending(true)
    setError('')
    try {
      await api.streamChatTurn({
        text,
        request_id: uniqueId('turn'),
        idempotency_key: uniqueId('turn-idem'),
        device_id: deviceId,
      }, (event, payload) => {
        if (event === 'text_delta') setStreamText(payload.text || '')
      })
      onDraftChange('')
      await refresh()
    } catch (failure) {
      setError(failure.message)
    } finally {
      setSending(false)
      setStreamText('')
    }
  }

  const keyFor = (proposal, action) => {
    const mapKey = `${proposal.id}:${proposal.data_version}:${action}`
    if (!confirmKeys.current.has(mapKey)) confirmKeys.current.set(mapKey, uniqueId(action))
    return confirmKeys.current.get(mapKey)
  }

  const confirmProposal = async (proposal) => {
    const result = await api.confirmStage3Proposal(proposal.id, {
      idempotency_key: keyFor(proposal, 'confirm'), device_id: deviceId,
      data_version: proposal.data_version,
    })
    await refresh()
    onAuthoritativeWrite?.()
    return result
  }

  const cancelProposal = async (proposal) => {
    const result = await api.cancelStage3Proposal(proposal.id, {
      idempotency_key: keyFor(proposal, 'cancel'), device_id: deviceId,
    })
    await refresh()
    return result
  }

  const editProposal = async (proposal, draft) => {
    const result = await api.editStage3Proposal(proposal.id, {
      idempotency_key: keyFor(proposal, 'edit'), data_version: proposal.data_version,
      occurred_on: draft.date || null,
      quantities: draft.quantityActionIndex == null ? {} : { [draft.quantityActionIndex]: draft.quantity },
      remove_action_indexes: draft.removeActionIndexes || [],
    })
    await refresh()
    return result
  }

  const resolveProduct = async (proposal, choice = null, createNew = false) => {
    const recognized = proposal.product_match?.recognized || {}
    const result = await api.resolveProposalProduct(proposal.id, {
      data_version: proposal.data_version,
      idempotency_key: keyFor(proposal, createNew ? 'resolve-new' : `resolve-${choice?.id}`),
      product_id: choice?.id || null,
      create_new: createNew,
      canonical_name: createNew ? recognized.name : null,
      brand: createNew ? recognized.brand : null,
      specification: createNew ? recognized.specification : null,
    })
    await refresh()
    return result
  }

  const regenerateProposal = async (proposal) => {
    const result = await api.regenerateStage3Proposal(proposal.id, {
      request_id: uniqueId('regenerate'), idempotency_key: keyFor(proposal, 'regenerate'),
      device_id: deviceId,
    })
    await refresh()
    return result
  }

  const renderBlock = (block) => {
    if (block.block_type === 'confirm_card') {
      const proposal = { ...block.payload, status: block.state, data_version: block.data_version }
      return (
        <ConfirmCard
          key={block.id}
          proposal={proposal}
          real
          onConfirm={() => confirmProposal(proposal)}
          onCancel={() => cancelProposal(proposal)}
          onEdit={(draft) => editProposal(proposal, draft)}
          onRegenerate={() => regenerateProposal(proposal)}
        />
      )
    }
    if (block.block_type === 'receipt_card') {
      return <ReceiptCard key={block.id} {...block.payload} />
    }
    if (block.block_type === 'product_match_card') {
      const proposal = { ...block.payload, status: block.state, data_version: block.data_version }
      return (
        <ProductMatchCard
          key={block.id}
          match={proposal.product_match}
          onChoose={(choice) => resolveProduct(proposal, choice, false)}
          onAddNew={() => resolveProduct(proposal, null, true)}
        />
      )
    }
    return null
  }

  let previousDate = null
  const rendered = messages.map((message) => {
    const showDate = message.session_date !== previousDate
    previousDate = message.session_date
    return (
      <Fragment key={message.id}>
        {showDate && <div className="v2-day" data-testid="date-separator">{dayLabel(message.session_date)}</div>}
        {message.content && message.message_type !== 'block' && (
          <div className={`v2-msg ${message.role === 'owner' ? 'owner' : 'assistant'}`}>{message.content}</div>
        )}
        {message.blocks?.map((block) => <div className="v2-msg-block" key={block.id}>{renderBlock(block)}</div>)}
      </Fragment>
    )
  })

  return (
    <div className="v2-chat" data-testid="chat-view">
      <div className="v2-chat-scroll">
        {hasMore && <button className="v2-link v2-load-earlier" onClick={loadEarlier}>加载更早消息</button>}
        {pending.length > 0 && <div className="v2-pending-banner">有 {pending.length} 项未完成确认，可跨日继续或放弃</div>}
        {loading && <div className="v2-state">正在恢复主对话…</div>}
        {!loading && messages.length === 0 && <div className="v2-msg assistant">你好，记账时请写明客户化名、已有服务、次数和日期。</div>}
        {rendered}
        {sending && <div className="v2-msg assistant"><span className="v2-spinner" /> {streamText || '正在保存并生成统一确认卡…'}</div>}
        {error && <div className="v2-msg-block"><ReceiptCard status="failure" title="请求失败" detail={`${error}；输入草稿已保留。`} onRetry={submit} /></div>}
        <div ref={bottomRef} />
      </div>
      <ChatComposer input={draftInput} onInputChange={onDraftChange} onSend={submit} sending={sending} onStop={() => setSending(false)} />
    </div>
  )
}
