// ConfirmCard：展示变化摘要、绝对日期、Mock权威预检查结果、原始表达；
// 主按钮“确认”，辅助“修改”“取消”。确认后切换为 Mock ReceiptCard，
// 并明确标记“阶段2演示数据，未写入真实账本”。
import { useState } from 'react'
import ReceiptCard from './ReceiptCard.jsx'

export default function ConfirmCard({ proposal, onConfirm, onCancel, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState({
    quantity: proposal?.quantity ?? 1,
    date: proposal?.absolute_date ?? '',
  })
  const [confirmed, setConfirmed] = useState(false)
  const [cancelled, setCancelled] = useState(false)

  if (!proposal) return null

  if (confirmed) {
    return (
      <div className="v2-block" data-testid="confirm-card">
        <ReceiptCard
          status="success"
          title="已确认（Mock）"
          detail="阶段2演示数据，未写入真实账本"
          result={[
            `${proposal.changes_summary || '操作'} · 绝对日期 ${draft.date}`,
            `原始表达：${proposal.original_expression || ''}`,
          ]}
        />
      </div>
    )
  }

  if (cancelled) {
    return (
      <div className="v2-block" data-testid="confirm-card">
        <ReceiptCard status="cancelled" title="已取消" detail="未写入任何数据（Mock）" />
      </div>
    )
  }

  return (
    <div className="v2-block v2-confirm" data-testid="confirm-card">
      <div className="v2-block-kicker">待确认（Mock）</div>
      <div className="v2-confirm-title">{proposal.title || '确认本次操作'}</div>

      <div className="v2-confirm-summary">
        <div className="v2-kv"><span className="k">将要发生的变化</span><span className="v">{proposal.changes_summary}</span></div>
        <div className="v2-kv"><span className="k">绝对日期</span><span className="v">{draft.date}</span></div>
        <div className="v2-kv"><span className="k">权威预检查</span><span className="v ok">{proposal.precheck || '余额充足，无冲突'}</span></div>
        <div className="v2-kv"><span className="k">原始表达</span><span className="v">{proposal.original_expression}</span></div>
      </div>

      {editing && (
        <div className="v2-edit-inline">
          <label>次数
            <input type="number" min="1" value={draft.quantity}
              onChange={(e) => setDraft((d) => ({ ...d, quantity: Number(e.target.value) }))} />
          </label>
          <label>日期
            <input type="date" value={draft.date}
              onChange={(e) => setDraft((d) => ({ ...d, date: e.target.value }))} />
          </label>
        </div>
      )}

      <div className="v2-confirm-actions">
        <button className="v2-btn secondary" onClick={() => { setEditing((e) => !e); onEdit?.(draft) }}>
          {editing ? '完成修改' : '修改'}
        </button>
        <button className="v2-btn secondary" onClick={() => { setCancelled(true); onCancel?.() }}>取消</button>
        <button className="v2-btn" onClick={() => { setConfirmed(true); onConfirm?.(draft) }}>确认</button>
      </div>
    </div>
  )
}
