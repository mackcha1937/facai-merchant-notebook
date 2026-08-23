// ProductMatchCard：exact / fuzzy / ambiguous / not_found / insufficient。
// - 单一近似显示一个；多候选最多显示3个；
// - 询问“请问是这个吗”；not_found 显示识别字段并询问是否新增；
export default function ProductMatchCard({ match, onChoose, onAddNew }) {
  if (!match) return null

  const { status } = match

  if (status === 'not_found') {
    return (
      <div className="v2-block v2-match" data-testid="product-match-card" data-status={status}>
        <div className="v2-block-kicker">产品匹配 · 未找到</div>
        <p className="v2-hint">已识别到：{match.recognized?.name || '未知产品'}。是否作为新产品草稿新增？</p>
        <div className="v2-kv"><span className="k">缺失资料</span><span className="v">{match.missing_fields?.join('、') || '无'}</span></div>
        <div className="v2-kv"><span className="k">新增后的影响</span><span className="v">可记账；资料待补充，暂不参与跨客户推荐</span></div>
        <div className="v2-actions">
          <button className="v2-btn" onClick={() => onAddNew?.(match)}>作为新产品</button>
        </div>
      </div>
    )
  }

  if (status === 'insufficient') {
    return (
      <div className="v2-block v2-match" data-testid="product-match-card" data-status={status}>
        <div className="v2-block-kicker">产品匹配 · 信息不足</div>
        <p className="v2-hint">只识别到“{match.recognized?.name || '—'}”，请补充品牌或规格。</p>
      </div>
    )
  }

  const candidates = match.candidates || (match.matched ? [match.matched] : [])

  return (
    <div className="v2-block v2-match" data-testid="product-match-card" data-status={status}>
      <div className="v2-block-kicker">产品匹配 · {status === 'exact' ? '精确' : status === 'fuzzy' ? '近似' : '多候选'}</div>
      <p className="v2-hint">请问是这个吗？</p>
      <div className="v2-candidates">
        {candidates.slice(0, 3).map((c) => (
          <button key={c.id} className="v2-candidate" onClick={() => onChoose?.(c)}>
            <span className="v2-candidate-main">
              <strong>{c.name}</strong>
              <span>{c.brand || '—'} · {c.spec || '—'}</span>
              <span>{c.match_method === 'embedding' ? '名称语义候选' : c.match_method === 'alias' ? '别名命中' : '字符匹配'} · {Math.round((c.score || 0) * 100)}%</span>
            </span>
            <span className="v2-chevron">›</span>
          </button>
        ))}
      </div>
      {status !== 'exact' && <button className="v2-link" onClick={() => onAddNew?.(match)}>都不是，作为新产品草稿</button>}
    </div>
  )
}
