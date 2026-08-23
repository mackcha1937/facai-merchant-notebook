// CustomerRecordCard：概况/客户事实/服务套餐/产品/跟进/账本历史。
// - 默认展示概况，支持收起；
// - 支持查看服务详情第二级，并可返回客户档案；
// - 支持从客户档案返回客户列表；
// - 演示服务类型较多时不铺开所有服务（分区收起）。
import { useState } from 'react'

const SECTIONS = [
  { key: 'overview', label: '概况' },
  { key: 'facts', label: '客户事实' },
  { key: 'services', label: '服务套餐' },
  { key: 'products', label: '产品' },
  { key: 'follow_ups', label: '跟进' },
  { key: 'history', label: '账本历史' },
]

export default function CustomerRecordCard({ record, onBackToList, onOpenService }) {
  const [active, setActive] = useState('overview')

  if (!record) return null
  const overview = record.overview || {
    since: '—',
    total_consumption_count: (record.recent_entries || []).filter((entry) => entry.entry_type !== 'package_purchase').length,
    total_spend_cents: (record.recent_entries || []).reduce((sum, entry) => sum + (entry.price_cents || 0), 0),
    service_type_count: record.service_type_count || 0,
    active_package_count: record.active_package_count || 0,
  }
  const facts = record.facts || []
  const services = (record.services || []).map((service) => ({
    ...service,
    id: service.id ?? service.service_id,
    name: service.name ?? service.service_name,
  }))
  const products = record.products || []
  const followUps = record.follow_ups || []
  const ledgerHistory = record.ledger_history || record.recent_entries || []

  return (
    <div className="v2-block v2-record" data-testid="customer-record-card">
      <div className="v2-path">
        <button className="v2-link" onClick={onBackToList}>← 返回客户列表</button>
      </div>
      <div className="v2-record-head">
        <span className="v2-avatar">{record.display_name.slice(0, 1)}</span>
        <div>
          <div className="v2-record-title">{record.display_name}</div>
          <div className="v2-muted">别名：{record.aliases.join('、') || '无'}</div>
        </div>
      </div>

      <div className="v2-tabs">
        {SECTIONS.map((s) => (
          <button key={s.key} className={`v2-tab ${active === s.key ? 'active' : ''}`} onClick={() => setActive(s.key)}>
            {s.label}
          </button>
        ))}
      </div>

      {active === 'overview' && (
        <div className="v2-section">
          <div className="v2-kv"><span className="k">成为客户</span><span className="v">{overview.since}</span></div>
          <div className="v2-kv"><span className="k">近期消费记录</span><span className="v">{overview.total_consumption_count} 次</span></div>
          <div className="v2-kv"><span className="k">近期金额</span><span className="v">¥{(overview.total_spend_cents / 100).toFixed(0)}</span></div>
          <div className="v2-kv"><span className="k">服务类型</span><span className="v">{overview.service_type_count} 类</span></div>
          <div className="v2-kv"><span className="k">有效套餐</span><span className="v">{overview.active_package_count} 个</span></div>
          {record.authoritative && <div className="v2-kv"><span className="k">数据版本</span><span className="v ok">权威 #{record.data_version}</span></div>}
        </div>
      )}

      {active === 'facts' && (
        <div className="v2-section">
          {facts.map((f) => (
            <div key={f.id} className="v2-kv">
              <span className="k">{f.type}{f.confirmed ? ' · 已确认' : ' · 待确认'}</span>
              <span className="v">{f.value}</span>
            </div>
          ))}
          {facts.length === 0 && <div className="v2-state">暂无已确认客户事实</div>}
        </div>
      )}

      {active === 'services' && (
        <div className="v2-section">
          {services.map((s) => (
            <button key={s.id} className="v2-candidate" onClick={() => onOpenService?.(s.id)}>
              <span className="v2-candidate-main">
                <strong>{s.name}</strong>
                <span>最近 {s.last_consumed_at} · {s.total_remaining_count != null ? `剩${s.total_remaining_count}次` : '单次'}</span>
              </span>
              <span className="v2-chevron">›</span>
            </button>
          ))}
          {services.length === 0 && <div className="v2-state">暂无服务数据</div>}
        </div>
      )}

      {active === 'products' && (
        <div className="v2-section">
          {products.map((p) => (
            <div key={p.id} className="v2-kv">
              <span className="k">{p.name}</span>
              <span className="v">最近 {p.last_purchased_at} · 共{p.purchase_count}次</span>
            </div>
          ))}
          {products.length === 0 && <div className="v2-state">暂无产品购买记录</div>}
        </div>
      )}

      {active === 'follow_ups' && (
        <div className="v2-section">
          {followUps.map((f) => (
            <div key={f.id} className="v2-kv">
              <span className="k">{f.type}</span>
              <span className="v">{f.summary}（{f.date}）</span>
            </div>
          ))}
          {followUps.length === 0 && <div className="v2-state">暂无跟进事项</div>}
        </div>
      )}

      {active === 'history' && (
        <div className="v2-section">
          {ledgerHistory.map((l) => (
            <div key={l.id} className="v2-kv">
              <span className="k">{l.name || l.service_name || l.product_name || '账本记录'}</span>
              <span className="v">{l.entry_type === 'product_purchase' ? '商品购买' : l.entry_type === 'package_consumption' ? '套餐核销' : '一次性服务'} · {l.occurred_on} · {l.quantity}次</span>
            </div>
          ))}
          {ledgerHistory.length === 0 && <div className="v2-state">暂无账本历史</div>}
        </div>
      )}
    </div>
  )
}
