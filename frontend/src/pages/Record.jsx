import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, yuanToCents, formatPrice } from '../api.js'

const ACTION_TYPE_LABEL = {
  create_package: '购买套餐',
  consume_service: '核销套餐',
  record_one_time_service: '一次性服务',
  record_product_purchase: '商品购买',
  query_customer: '查询客户',
}

export default function Record() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [proposal, setProposal] = useState(null)
  const [services, setServices] = useState([])
  const [confirming, setConfirming] = useState(false)
  const [confirmResult, setConfirmResult] = useState(null)

  const loadServices = useCallback(async () => {
    try {
      setServices((await api.getServices()).filter((s) => s.status === 'active'))
    } catch (e) { /* 忽略 */ }
  }, [])

  useEffect(() => { loadServices() }, [loadServices])

  const run = async () => {
    const value = text.trim()
    if (!value) { setError('请输入要记录的内容'); return }
    setLoading(true)
    setError('')
    setProposal(null)
    setConfirmResult(null)
    try {
      const data = await api.interpret(value)
      setProposal(data)
      if (data.error) setError(data.error)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page">
      <h1>记账（自然语言）</h1>
      <p className="subtitle">用一句话记录，例如：小蓝今天肩颈按摩1次。</p>

      <section className="card">
        <textarea
          className="input-area"
          rows={3}
          placeholder="例如：小蓝来店里做了面部清洁，清痘，还买了一个面霜。"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="row-actions" style={{ marginTop: 10 }}>
          <button onClick={run} disabled={loading}>{loading ? '解析中…' : '解析并预览'}</button>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

      {proposal && !proposal.error && !confirmResult && (
        <ConfirmEditor
          proposal={proposal}
          services={services}
          confirming={confirming}
          setConfirming={setConfirming}
          onError={setError}
          onConfirmed={setConfirmResult}
        />
      )}

      {confirmResult && <ConfirmResultView result={confirmResult} />}
    </main>
  )
}

function ConfirmEditor({ proposal, services, confirming, setConfirming, onError, onConfirmed }) {
  const cm = proposal.customer_match || {}
  const [selectedCustomerId, setSelectedCustomerId] = useState(
    cm.status === 'exact' ? cm.candidate_ids[0] ?? null : cm.status === 'fuzzy' ? cm.candidates[0]?.id ?? null : null,
  )
  const [newName, setNewName] = useState(cm.new_customer_name || '')
  const [newAliases, setNewAliases] = useState('')
  const [actions, setActions] = useState(() => initActions(proposal.actions))
  const [customerDetail, setCustomerDetail] = useState(null)

  useEffect(() => {
    let cancelled = false
    if (selectedCustomerId != null) {
      api.getCustomer(selectedCustomerId).then((d) => { if (!cancelled) setCustomerDetail(d) }).catch(() => {})
    } else {
      setCustomerDetail(null)
    }
    return () => { cancelled = true }
  }, [selectedCustomerId])

  const updateAction = (index, patch) => setActions((prev) => prev.map((a, i) => (i === index ? { ...a, ...patch } : a)))
  const removeAction = (index) => setActions((prev) => prev.filter((_, i) => i !== index))

  const cardOptions = (action) => {
    if (action.type !== 'consume_service' || !action.service_id || !customerDetail) return []
    return (customerDetail.packages || []).filter((p) => p.service_id === action.service_id && p.status !== 'inactive')
  }

  const confirm = async () => {
    const customer = selectedCustomerId != null
      ? { customer_id: selectedCustomerId }
      : { new_customer: { display_name: newName.trim(), aliases: newAliases.split(/[,，]/).map((s) => s.trim()).filter(Boolean) } }

    if (selectedCustomerId == null && !newName.trim()) { onError('请选择已有客户或填写新客户化名'); return }

    for (const a of actions) {
      if (a.type === 'consume_service') {
        const cards = cardOptions(a)
        if (cards.length > 1 && a.package_id == null) { onError('该客户有多张同类套餐卡，请选择使用哪一张'); return }
      }
    }

    const payload = {
      customer,
      actions: actions.map((a) => ({
        type: a.type,
        service_id: a.service_id ?? null,
        package_id: a.type === 'consume_service' ? (a.package_id ?? null) : null,
        product_name: a.type === 'record_product_purchase' ? (a.product_name || null) : null,
        quantity: a.quantity != null ? Number(a.quantity) : null,
        price_cents: yuanToCents(a.price),
        total_count: a.type === 'create_package' ? Number(a.total_count) : null,
      })),
    }

    setConfirming(true)
    onError('')
    try {
      onConfirmed(await api.confirmProposal(proposal.id, payload))
    } catch (e) {
      onError(e.message)
    } finally {
      setConfirming(false)
    }
  }

  return (
    <section className="card">
      <h2>确认预览（可修改）</h2>

      <div className="block">
        <strong>客户</strong>
        {cm.status === 'not_found' ? (
          <div className="edit-grid" style={{ marginTop: 8 }}>
            <label>新客户化名 <input value={newName} onChange={(e) => setNewName(e.target.value)} /></label>
            <label>别名（可选，逗号分隔）<input value={newAliases} onChange={(e) => setNewAliases(e.target.value)} /></label>
            <p className="hint">将创建新客户，并继续执行下方操作。</p>
          </div>
        ) : (
          <div className="candidate-list">
            {(cm.candidates || []).map((c) => (
              <label key={c.id} className="candidate">
                <input type="radio" name="customer" checked={selectedCustomerId === c.id} onChange={() => setSelectedCustomerId(c.id)} />
                {c.display_name}{c.aliases && c.aliases.length > 0 && `（${c.aliases.join('、')}）`}
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="block">
        <strong>操作（{actions.length} 项）</strong>
        <ul className="list">
          {actions.map((a, i) => (
            <li key={i} className="list-item column">
              <div className="row-actions">
                <span className="tag tag-ledger">{ACTION_TYPE_LABEL[a.type] || a.type}</span>
                <button className="danger" onClick={() => removeAction(i)}>删除此项</button>
              </div>
              <ActionFields action={a} index={i} services={services} cards={cardOptions(a)} updateAction={updateAction} />
            </li>
          ))}
          {actions.length === 0 && <li className="muted empty">（无操作）</li>}
        </ul>
      </div>

      {proposal.needs_clarification && proposal.clarification_question && (
        <div className="block"><span className="tag tag-package">需要澄清</span><p className="hint">系统提问：{proposal.clarification_question}</p></div>
      )}

      <div className="row-actions" style={{ marginTop: 12 }}>
        <button onClick={confirm} disabled={confirming || actions.length === 0}>{confirming ? '写入中…' : '确认写入'}</button>
        <span className="muted">确认后才真正写入。</span>
      </div>
    </section>
  )
}

function ActionFields({ action, index, services, cards, updateAction }) {
  const isServiceAction = ['consume_service', 'record_one_time_service', 'create_package'].includes(action.type)
  const isProductAction = action.type === 'record_product_purchase'
  if (action.type === 'query_customer') return <div className="muted">查询客户信息（不写入）</div>

  return (
    <div className="edit-grid">
      {isServiceAction && (
        <label>服务
          <select value={action.service_id ?? ''} onChange={(e) => updateAction(index, { service_id: Number(e.target.value) || null })}>
            <option value="">选择服务…</option>
            {services.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
      )}
      {isProductAction && (
        <label>商品名称 <input value={action.product_name || ''} onChange={(e) => updateAction(index, { product_name: e.target.value })} /></label>
      )}
      {action.type === 'create_package' && (
        <label>总次数 <input type="number" min="1" value={action.total_count ?? ''} onChange={(e) => updateAction(index, { total_count: e.target.value })} /></label>
      )}
      {action.type !== 'create_package' && (
        <label>数量 <input type="number" min="1" value={action.quantity ?? 1} onChange={(e) => updateAction(index, { quantity: e.target.value })} /></label>
      )}
      {action.type === 'consume_service' && cards.length > 1 && (
        <label>使用哪张卡
          <select value={action.package_id ?? ''} onChange={(e) => updateAction(index, { package_id: Number(e.target.value) || null })}>
            <option value="">请选择…</option>
            {cards.map((p) => <option key={p.id} value={p.id}>卡#{p.id}（总{p.total_count}·已用{p.used_count}·剩{p.remaining_count}）</option>)}
          </select>
        </label>
      )}
      <label>价格（元，可选）<input value={action.price ?? ''} onChange={(e) => updateAction(index, { price: e.target.value })} /></label>
    </div>
  )
}

function initActions(rawActions) {
  return (rawActions || []).map((a) => ({
    type: a.type,
    service_id: a.service_match?.resolved_service_id ?? null,
    package_id: null,
    product_name: a.product_name ?? '',
    quantity: a.quantity ?? (a.type === 'query_customer' ? null : 1),
    price: a.price_cents != null ? String(a.price_cents / 100) : '',
    total_count: a.total_count ?? '',
  }))
}

function ConfirmResultView({ result }) {
  const [detail, setDetail] = useState(null)
  useEffect(() => {
    if (result.customer?.id) api.getCustomer(result.customer.id).then(setDetail).catch(() => {})
  }, [result])

  return (
    <section className="card">
      <h2>写入结果</h2>
      <p><span className="tag tag-active">已写入</span> 客户：{result.customer?.display_name}</p>
      <ul className="list">
        {result.results.map((r, i) => <li key={i} className="list-item column"><strong>{r.message}</strong></li>)}
      </ul>
      {detail && (
        <div className="block">
          <strong>账本核对</strong>
          {detail.packages.map((p) => (
            <div key={p.id} className="candidate">{p.service_name}：总 {p.total_count} 次 · 已用 {p.used_count} 次 · 剩余 {p.remaining_count} 次{formatPrice(p.price_cents) !== '—' && ` · ${formatPrice(p.price_cents)} 元`}</div>
          ))}
          {detail.packages.length === 0 && <p className="muted">（暂无套餐卡）</p>}
          <p className="hint"><Link to={`/customers/${result.customer?.id}`}>查看完整账本 →</Link></p>
        </div>
      )}
    </section>
  )
}
