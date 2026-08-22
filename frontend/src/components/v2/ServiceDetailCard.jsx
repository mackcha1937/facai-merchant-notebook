// 服务详情（第二级）：从客户档案进入，可返回客户档案。
export default function ServiceDetailCard({ service, customerName, onBack }) {
  if (!service) return null
  return (
    <div className="v2-block v2-record" data-testid="service-detail-card">
      <div className="v2-path">
        <button className="v2-link" onClick={onBack}>← 返回 {customerName} 档案</button>
      </div>
      <div className="v2-record-title">{service.name}</div>
      <div className="v2-kv"><span className="k">服务类型数</span><span className="v">{service.service_type_count}</span></div>
      <div className="v2-kv"><span className="k">最近消费</span><span className="v">{service.last_consumed_at}</span></div>
      <div className="v2-kv"><span className="k">剩余次数</span><span className="v">{service.total_remaining_count ?? '—'}</span></div>
      <p className="v2-hint">（阶段2演示：服务详情第二级，可逐层返回）</p>
    </div>
  )
}
