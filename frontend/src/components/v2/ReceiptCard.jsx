// ReceiptCard：成功/失败/取消/冲突/已删除/已恢复。
// - 成功卡自动压缩（结果行收起，关键标记仍可见），可展开查看当时信息；
// - 失败在原位置显示重试；
// - 历史回执保留当时信息。
import { useState } from 'react'

const STATUS_META = {
  success: { label: '成功', className: 'ok' },
  failure: { label: '失败', className: 'bad' },
  cancelled: { label: '已取消', className: 'pending' },
  conflict: { label: '冲突', className: 'warn' },
  deleted: { label: '已删除', className: 'bad' },
  restored: { label: '已恢复', className: 'ok' },
}

export default function ReceiptCard({ status = 'success', title = '', detail = '', result = null, onRetry }) {
  const [expanded, setExpanded] = useState(false)
  const meta = STATUS_META[status] || STATUS_META.success
  const compressible = status === 'success'

  return (
    <div className="v2-receipt" data-status={status} data-testid="receipt-card">
      <div className="v2-receipt-head">
        <span className={`v2-receipt-dot ${meta.className}`}>{meta.label}</span>
        <span className="v2-receipt-title">{title || meta.label}</span>
        {compressible && (
          <button className="v2-link" onClick={() => setExpanded((e) => !e)} aria-label="展开或收起">
            {expanded ? '收起' : '展开'}
          </button>
        )}
      </div>

      {detail && <div className="v2-receipt-detail">{detail}</div>}

      {(status !== 'success' || expanded) && result && (
        <div className="v2-receipt-result">
          {Array.isArray(result)
            ? result.map((r, i) => <div key={i} className="v2-receipt-line">{r}</div>)
            : <div className="v2-receipt-line">{String(result)}</div>}
        </div>
      )}

      {status === 'failure' && onRetry && (
        <button className="v2-btn secondary" onClick={onRetry}>重试</button>
      )}
    </div>
  )
}
