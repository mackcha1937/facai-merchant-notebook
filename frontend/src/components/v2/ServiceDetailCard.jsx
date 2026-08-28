// 服务详情（第二级）：从客户档案进入，可返回客户档案。
export default function ServiceDetailCard({ service, customerName }) {
  if (!service) return null
  const name = service.name || service.service_name
  const remaining = service.total_remaining_count ?? (service.packages || []).reduce((sum, item) => sum + (item.remaining_count || 0), 0)
  return (
    <div className="v2-block v2-record" data-testid="service-detail-card">
      <div className="v2-block-kicker">{customerName} · 服务档案</div>
      <div className="v2-record-title">{name}</div>
      <div className="v2-kv"><span className="k">套餐数量</span><span className="v">{service.packages?.length ?? service.service_type_count ?? 0}</span></div>
      <div className="v2-kv"><span className="k">最近消费</span><span className="v">{service.last_consumed_at}</span></div>
      <div className="v2-kv"><span className="k">权威剩余次数</span><span className="v ok">{remaining ?? '—'}</span></div>
      <p className="v2-hint">每次展开均从后端读取最新账本派生余额。</p>
    </div>
  )
}
