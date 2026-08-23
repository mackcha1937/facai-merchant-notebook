import { useEffect, useState } from 'react'
import ReceiptCard from './ReceiptCard.jsx'

export default function ConfirmCard({ proposal, onConfirm, onCancel, onEdit, onRegenerate, real = false }) {
  const [editing, setEditing] = useState(false)
  const quantityActionIndex = proposal?.actions?.findIndex((action) => action.quantity != null && action.type !== 'upsert_customer_fact') ?? -1
  const [draft, setDraft] = useState({
    quantity: quantityActionIndex >= 0 ? proposal?.actions?.[quantityActionIndex]?.quantity : (proposal?.quantity ?? 1),
    quantityActionIndex: quantityActionIndex >= 0 ? quantityActionIndex : null,
    date: proposal?.absolute_date ?? '',
    removeActionIndexes: [],
  })
  const [localState, setLocalState] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setDraft({
      quantity: quantityActionIndex >= 0 ? proposal?.actions?.[quantityActionIndex]?.quantity : (proposal?.quantity ?? 1),
      quantityActionIndex: quantityActionIndex >= 0 ? quantityActionIndex : null,
      date: proposal?.absolute_date ?? '',
      removeActionIndexes: [],
    })
    setLocalState(null)
  }, [proposal?.id, proposal?.data_version, proposal?.absolute_date, quantityActionIndex])

  if (!proposal) return null

  const state = localState?.status || proposal.status || 'pending'
  if (state === 'confirmed' || state === 'success') {
    const lines = proposal.result?.results?.map((item) => item.message) || localState?.result || [
      `${proposal.changes_summary || '操作'} · 绝对日期 ${draft.date}`,
    ]
    return <ReceiptCard status="success" title={real ? '已确认并写入' : '已确认（Mock）'} detail={real ? '权威结果已由后端事务提交' : '阶段2演示数据，未写入真实账本'} result={lines} />
  }
  if (state === 'cancelled') {
    return <ReceiptCard status="cancelled" title="已取消" detail={real ? '未写入任何账本数据' : '未写入任何数据（Mock）'} />
  }
  if (state === 'conflict') {
    return <ReceiptCard status="conflict" title="确认冲突" detail={localState?.detail || '另一设备已处理；没有重复写入。'} result={localState?.result} />
  }
  if (state === 'stale' || state === 'expired') {
    return (
      <div className="v2-block" data-testid="confirm-card">
        <ReceiptCard
          status={state}
          title={state === 'stale' ? '数据已变化' : '确认卡已过期'}
          detail="旧确认卡禁止直接执行，请读取当前权威数据后重新确认。"
        />
        {onRegenerate && <button className="v2-btn" disabled={busy} onClick={async () => {
          setBusy(true)
          try { await onRegenerate() } catch (error) { setLocalState({ status: 'conflict', detail: error.message }) } finally { setBusy(false) }
        }}>重新生成确认卡</button>}
      </div>
    )
  }

  const run = async (kind) => {
    if (!real) {
      setLocalState({ status: kind === 'confirm' ? 'success' : 'cancelled' })
      if (kind === 'confirm') onConfirm?.(draft)
      else onCancel?.()
      return
    }
    setBusy(true)
    try {
      if (kind === 'confirm') {
        const result = await onConfirm?.(draft)
        setLocalState({ status: 'success', result: result?.results?.map((item) => item.message) })
      } else if (kind === 'cancel') {
        await onCancel?.()
        setLocalState({ status: 'cancelled' })
      } else {
        await onEdit?.(draft)
        setEditing(false)
      }
    } catch (error) {
      const payload = error.payload || {}
      setLocalState({
        status: payload.status === 'stale' || payload.status === 'expired' ? payload.status : 'conflict',
        detail: error.message,
        result: payload.differences || payload.original_result?.results?.map((item) => item.message),
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="v2-block v2-confirm" data-testid="confirm-card">
      <div className="v2-block-kicker">{real ? '待确认 · 尚未写入' : '待确认（Mock）'}</div>
      <div className="v2-confirm-title">{proposal.title || '确认本次操作'}</div>
      <div className="v2-confirm-summary">
        <div className="v2-kv"><span className="k">将要发生的变化</span><span className="v">{proposal.changes_summary}</span></div>
        <div className="v2-kv"><span className="k">绝对日期</span><span className="v">{draft.date}</span></div>
        <div className="v2-kv"><span className="k">权威预检查</span><span className="v ok">{proposal.precheck || '确认时重新检查'}</span></div>
        <div className="v2-kv"><span className="k">原始表达</span><span className="v">{proposal.original_expression}</span></div>
      </div>
      {(proposal.actions || []).map((action, index) => action.type === 'upsert_customer_fact' ? (
        <div className="v2-fact-candidate" key={`fact-${index}`} data-sensitive={action.sensitivity_level === 'sensitive'}>
          <div><strong>{action.sensitivity_level === 'sensitive' ? '敏感/不适事实（单列）' : '客户事实'}</strong> · {action.fact_type}</div>
          <div>{action.previous_value ? `${action.previous_value} → ` : ''}{action.display_value}</div>
          <div className="v2-muted">证据：{action.evidence_text} · 置信度 {Math.round((action.confidence || 0) * 100)}%</div>
          {editing && <label><input type="checkbox" checked={!draft.removeActionIndexes.includes(index)} onChange={(event) => setDraft((current) => ({
            ...current,
            removeActionIndexes: event.target.checked
              ? current.removeActionIndexes.filter((item) => item !== index)
              : [...current.removeActionIndexes, index],
          }))} /> 保留此事实</label>}
        </div>
      ) : action.type === 'delete_customer_fact' ? (
        <div className="v2-fact-candidate" key={`delete-fact-${index}`} data-sensitive="true">
          <div><strong>待撤销客户事实</strong> · {action.fact_type}</div>
          <div>{action.display_value}</div>
          <div className="v2-muted">店主原话：{action.evidence_text}；确认前不会删除。</div>
        </div>
      ) : action.type === 'record_product_purchase' ? (
        <div className="v2-kv" key={`product-${index}`}><span className="k">产品实体</span><span className="v">{action.product_name || action.canonical_name} · {action.create_product ? '新增草稿/资料待补充' : `产品 #${action.product_id}`}</span></div>
      ) : null)}
      {editing && (
        <div className="v2-edit-inline">
          {draft.quantityActionIndex != null && <label>数量<input type="number" min="1" value={draft.quantity} onChange={(e) => setDraft((d) => ({ ...d, quantity: Number(e.target.value) }))} /></label>}
          {draft.date && <label>日期<input type="date" value={draft.date} onChange={(e) => setDraft((d) => ({ ...d, date: e.target.value }))} /></label>}
        </div>
      )}
      <div className="v2-confirm-actions">
        <button className="v2-btn secondary" disabled={busy} onClick={() => editing ? run('edit') : setEditing(true)}>{editing ? '保存修改' : '修改'}</button>
        <button className="v2-btn secondary" disabled={busy} onClick={() => run('cancel')}>取消</button>
        <button className="v2-btn" disabled={busy} onClick={() => run('confirm')}>{busy ? '处理中…' : '确认'}</button>
      </div>
    </div>
  )
}
