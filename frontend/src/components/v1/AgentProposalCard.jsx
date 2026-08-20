import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'

const ACTION_LABEL = {
  create_package: '购买套餐',
  consume_service: '核销套餐',
  record_one_time_service: '一次性服务',
  record_product_purchase: '商品购买',
  query_customer: '查询客户',
}

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function formatDate(iso) {
  if (!iso) return ''
  const [y, m, d] = String(iso).slice(0, 10).split('-')
  return `${y}年${Number(m)}月${Number(d)}日`
}

function initActions(raw) {
  return (raw || []).map((a) => ({
    type: a.type,
    service_id: a.service_match?.resolved_service_id ?? null,
    package_id: null,
    product_name: a.product_name ?? '',
    quantity: a.quantity ?? (a.type === 'query_customer' ? null : 1),
    price_cents: a.price_cents ?? null,
    total_count: a.total_count ?? '',
    occurred_on: today(),
  }))
}

export default function AgentProposalCard({ proposal, onConfirmed }) {
  const cm = proposal.customer_match || {}
  const [customerId, setCustomerId] = useState(
    cm.status === 'exact' ? cm.candidate_ids[0] ?? null : cm.status === 'fuzzy' ? cm.candidates[0]?.id ?? null : null,
  )
  const [newName, setNewName] = useState(cm.new_customer_name || '')
  const [newAliases, setNewAliases] = useState('')
  const [actions, setActions] = useState(() => initActions(proposal.actions))
  const [editing, setEditing] = useState(true)
  const [preview, setPreview] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [confirmed, setConfirmed] = useState(null)
  const [error, setError] = useState('')

  const buildPayload = () => {
    const customer = customerId != null
      ? { customer_id: customerId }
      : { new_customer: { display_name: newName.trim(), aliases: newAliases.split(/[,，]/).map((s) => s.trim()).filter(Boolean) } }
    const payloadActions = actions.map((a) => ({
      type: a.type,
      service_id: a.service_id ?? null,
      package_id: a.type === 'consume_service' ? (a.package_id ?? null) : null,
      product_name: a.type === 'record_product_purchase' ? (a.product_name || null) : null,
      quantity: a.quantity != null ? Number(a.quantity) : null,
      price_cents: a.price_cents ?? null,
      total_count: a.type === 'create_package' ? Number(a.total_count) : null,
      occurred_on: a.occurred_on || null,
    }))
    return { customer, actions: payloadActions }
  }

  const runPrecheck = async () => {
    if (customerId == null && !newName.trim()) return
    try {
      const data = await api.precheckProposal(proposal.id, buildPayload())
      setPreview(data)
      setError('')
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    if (customerId != null || cm.status === 'not_found') {
      runPrecheck()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId])

  const updateAction = (i, patch) => {
    setActions((prev) => prev.map((a, idx) => (idx === i ? { ...a, ...patch } : a)))
  }

  const removeAction = (i) => {
    setActions((prev) => prev.filter((_, idx) => idx !== i))
  }

  const canConfirm = () => {
    if (actions.length === 0) return false
    if (customerId == null && !newName.trim()) return false
    const hasBad = (preview?.actions || []).some((a) => !a.ok)
    if (hasBad) return false
    return true
  }

  const confirm = async () => {
    setConfirming(true)
    setError('')
    try {
      const data = await api.confirmProposal(proposal.id, buildPayload())
      setConfirmed(data)
      onConfirmed?.(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setConfirming(false)
    }
  }

  if (confirmed) {
    return (
      <div className="v1-confirm-card">
        <div className="v1-confirm-head">
          <div className="v1-confirm-kicker"><span className="v1-success-dot">已入账</span></div>
          <div className="v1-confirm-title">写入成功</div>
        </div>
        <div className="v1-confirm-body">
          {confirmed.results.map((r, i) => (
            <div key={i} className="v1-action-item">
              <strong style={{ color: 'var(--c-success)' }}>{r.message}</strong>
              {r.occurred_on && <div className="v1-action-meta">入账日期：{formatDate(r.occurred_on)}</div>}
            </div>
          ))}
        </div>
        <div className="v1-confirm-actions">
          <Link className="v1-btn" to={`/customers/${confirmed.customer?.id}`} style={{ textAlign: 'center', textDecoration: 'none', lineHeight: '44px', gridColumn: '1 / -1' }}>
            查看客户账本 →
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="v1-confirm-card">
      <div className="v1-confirm-head">
        <div className="v1-confirm-kicker">
          <span>确认后才会写入</span>
          <span className="v1-state-dot">{confirming ? '写入中…' : '待确认'}</span>
        </div>
        <div className="v1-confirm-title">
          {cm.status === 'not_found' ? (newName || cm.new_customer_name || '新客户') : (proposal.customer_query || '')}
        </div>
        <div className="v1-confirm-subtitle">识别出 {actions.length} 项操作</div>
      </div>

      {/* 客户选择 */}
      {cm.status !== 'not_found' && (cm.status === 'ambiguous' || cm.status === 'fuzzy') && (
        <div className="v1-confirm-candidates">
          <p className="v1-hint">{cm.status === 'ambiguous' ? '有多个近似客户，请选择：' : '请问是这位客户吗？'}</p>
          {(cm.candidates || []).map((c) => (
            <label key={c.id} className="v1-candidate">
              <input type="radio" name="cust" checked={customerId === c.id} onChange={() => setCustomerId(c.id)} />
              {c.display_name}{c.aliases?.length > 0 && `（${c.aliases.join('、')}）`}
            </label>
          ))}
        </div>
      )}
      {cm.status === 'not_found' && (
        <div className="v1-confirm-candidates">
          <p className="v1-hint">系统未找到该客户，确认后将创建新客户。</p>
          <div className="v1-inline-form">
            <input placeholder="新客户化名" value={newName} onChange={(e) => setNewName(e.target.value)} />
            <input placeholder="别名（可选）" value={newAliases} onChange={(e) => setNewAliases(e.target.value)} />
          </div>
        </div>
      )}

      {/* 操作列表 */}
      <div className="v1-confirm-body">
        {actions.map((a, i) => {
          const pv = preview?.actions?.[i]
          return (
            <div key={i} className="v1-action-item">
              <div className="v1-action-line">
                <span className="v1-tag-mini">{ACTION_LABEL[a.type] || a.type}</span>
                <strong>
                  {a.type === 'record_product_purchase' ? (a.product_name || '商品') : ''}
                  {a.type === 'record_product_purchase' ? '' : ''}
                </strong>
                {a.type !== 'record_product_purchase' && a.service_id != null && (
                  <span className="v1-muted">（服务已选）</span>
                )}
                {a.type === 'query_customer' && <span className="v1-muted">查询客户</span>}
              </div>

              {a.type !== 'query_customer' && (
                <>
                  <div className="v1-action-meta">
                    {a.type === 'create_package' ? `总次数 ${a.total_count || '—'}` : `本次 ${a.quantity ?? 1} 次`}
                    {a.price_cents != null ? ` · ¥${(a.price_cents / 100).toFixed(2)}` : ''}
                  </div>
                  <div className="v1-edit-row">
                    <label>
                      次数
                      <input type="number" min="1" value={a.quantity ?? 1}
                        onChange={(e) => updateAction(i, { quantity: e.target.value })} />
                    </label>
                    <label>
                      日期
                      <input type="date" value={a.occurred_on}
                        onChange={(e) => updateAction(i, { occurred_on: e.target.value })} />
                    </label>
                  </div>
                  {/* 多卡选择 */}
                  {a.type === 'consume_service' && pv && !pv.ok && pv.candidates && (
                    <div className="v1-edit-row">
                      <label>
                        选择套餐卡
                        <select value={a.package_id ?? ''} onChange={(e) => updateAction(i, { package_id: Number(e.target.value) || null })}>
                          <option value="">请选择…</option>
                          {pv.candidates.map((c) => (
                            <option key={c.id} value={c.id}>卡#{c.id}（剩{c.remaining_count}/{c.total_count}）</option>
                          ))}
                        </select>
                      </label>
                    </div>
                  )}
                  {/* 余额预览 */}
                  {pv && pv.ok && pv.preview && (
                    <div className="v1-action-preview">
                      {a.type === 'consume_service' && `确认后：累计使用 ${pv.preview.used_after}/${pv.preview.total_count} 次，剩余 ${pv.preview.remaining_count} 次`}
                      {a.type === 'create_package' && `确认后：新建套餐 ${pv.preview.total_count} 次`}
                    </div>
                  )}
                  {pv && !pv.ok && pv.error && (
                    <div className="v1-action-error">{pv.error}</div>
                  )}
                  <button className="v1-link-btn" onClick={() => removeAction(i)}>移除此项</button>
                </>
              )}
            </div>
          )
        })}
        {actions.length === 0 && <div className="v1-muted">（无操作）</div>}
      </div>

      {proposal.needs_clarification && proposal.clarification_question && (
        <div className="v1-confirm-candidates">
          <span className="v1-tag-mini">需要澄清</span>
          <p className="v1-hint">{proposal.clarification_question}</p>
        </div>
      )}

      {error && <div className="v1-error-banner" style={{ margin: '0 14px 8px' }}>{error}</div>}

      <div className="v1-confirm-actions">
        <button className="v1-btn secondary" onClick={() => { runPrecheck() }}>重新检查</button>
        <button className="v1-btn" onClick={confirm} disabled={confirming || !canConfirm()}>
          {confirming ? '写入中…' : '确认入账'}
        </button>
      </div>
    </div>
  )
}
