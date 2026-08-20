const ACTION_LABEL = {
  create_package: '购买套餐',
  consume_service: '核销套餐',
  record_one_time_service: '一次性服务',
  record_product_purchase: '商品购买',
  query_customer: '查询客户',
}

const CUSTOMER_STATUS_LABEL = {
  exact: '精确匹配',
  fuzzy: '近似匹配',
  ambiguous: '多个候选',
  not_found: '未找到（新客户）',
}

function formatDate(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split('-')
  return `${y}年${Number(m)}月${Number(d)}日`
}

function today() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

export default function AgentProposalCard({ proposal }) {
  const cm = proposal.customer_match || {}
  const actions = proposal.actions || []

  return (
    <div className="v1-confirm-card">
      <div className="v1-confirm-head">
        <div className="v1-confirm-kicker">
          <span>确认后才会写入</span>
          <span className="v1-state-dot">本阶段不写入</span>
        </div>
        <div className="v1-confirm-title">{cm.status === 'not_found' ? cm.new_customer_name || '新客户' : proposal.customer_query}</div>
        <div className="v1-confirm-subtitle">
          {cm.status !== 'not_found' && (
            <span className="v1-tag-mini">{CUSTOMER_STATUS_LABEL[cm.status] || cm.status}</span>
          )}
        </div>
      </div>

      {cm.status === 'ambiguous' && cm.candidates && cm.candidates.length > 1 && (
        <div className="v1-confirm-candidates">
          <p className="v1-hint">有多个近似客户，本次为您展示前3位，请问有您咨询的客户吗？</p>
          {cm.candidates.map((c) => (
            <div key={c.id} className="v1-candidate">
              {c.display_name}{c.aliases?.length > 0 && `（${c.aliases.join('、')}）`}
            </div>
          ))}
        </div>
      )}

      {cm.status === 'fuzzy' && cm.candidates && cm.candidates.length === 1 && (
        <div className="v1-confirm-candidates">
          <p className="v1-hint">请问是这位客户吗？</p>
          <div className="v1-candidate">{cm.candidates[0].display_name}{cm.candidates[0].aliases?.length > 0 && `（${cm.candidates[0].aliases.join('、')}）`}</div>
        </div>
      )}

      {cm.status === 'not_found' && (
        <div className="v1-confirm-candidates">
          <p className="v1-hint">系统未找到该客户，确认时会询问是否新增。</p>
        </div>
      )}

      <div className="v1-confirm-body">
        {actions.map((a, i) => (
          <div key={i} className="v1-action-item">
            <div className="v1-action-line">
              <span className="v1-tag-mini">{ACTION_LABEL[a.type] || a.type}</span>
              <strong>
                {a.type === 'record_product_purchase' ? (a.product_name || '商品') : (a.service_name || '')}
              </strong>
            </div>
            <div className="v1-action-meta">
              {a.type === 'create_package' ? `总次数 ${a.total_count ?? '—'}` : `本次 ${a.quantity ?? 1} 次`}
              {a.purchased_on ? ` · ${formatDate(a.purchased_on)}` : ''}
              {a.price_cents != null ? ` · ¥${(a.price_cents / 100).toFixed(2)}` : ''}
            </div>
            <div className="v1-action-date">核销/消费日期：{formatDate(today())}</div>
            {a.service_match && a.service_match.status === 'fuzzy' && a.service_match.candidates?.[0] && (
              <div className="v1-action-meta">建议服务：{a.service_match.candidates[0].name}</div>
            )}
          </div>
        ))}
        {actions.length === 0 && (
          <div className="v1-action-meta">（无操作）</div>
        )}
      </div>

      {proposal.needs_clarification && proposal.clarification_question && (
        <div className="v1-confirm-candidates">
          <span className="v1-tag-mini">需要澄清</span>
          <p className="v1-hint">{proposal.clarification_question}</p>
        </div>
      )}

      <div className="v1-confirm-actions">
        <button className="v1-btn secondary" disabled>修改</button>
        <button className="v1-btn" disabled title="阶段2只预览，阶段3开放写入">确认入账（阶段3开放）</button>
      </div>
      <p className="v1-hint" style={{ padding: '0 14px 14px' }}>
        AI 可能理解有误，写入前会请你确认。本阶段仅预览解析结果，不写入数据库。
      </p>
    </div>
  )
}
