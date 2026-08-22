// CustomerIndexCard：全部客户 / 搜索客户或别名 / 筛选（全部/待跟进/有待确认资料）/
// 排序（最近消费/最近更新）/ 点击查看档案 / 返回恢复搜索词、筛选、排序和滚动位置。
import { useEffect, useRef, useState } from 'react'

const FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'follow_up', label: '待跟进' },
  { key: 'pending_confirm', label: '有待确认资料' },
]

const SORTS = [
  { key: 'recent_consumption', label: '最近消费' },
  { key: 'recent_update', label: '最近更新' },
]

export default function CustomerIndexCard({ customers = [], onOpenCustomer, onBack, saved = {}, onStateChange }) {
  const [query, setQuery] = useState(saved.query || '')
  const [filter, setFilter] = useState(saved.filter || 'all')
  const [sort, setSort] = useState(saved.sort || 'recent_consumption')
  const listRef = useRef(null)

  useEffect(() => {
    if (listRef.current && saved.scrollPosition) {
      listRef.current.scrollTop = saved.scrollPosition
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const report = (patch) => {
    onStateChange?.({ query, filter, sort, scrollPosition: listRef.current?.scrollTop || 0, ...patch })
  }

  const filtered = customers.filter((c) => {
    const q = query.trim().toLowerCase()
    if (q) {
      const hay = `${c.display_name} ${(c.aliases || []).join(' ')}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    if (filter === 'follow_up') return c.follow_up
    if (filter === 'pending_confirm') return c.unread_count > 0
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'recent_consumption') return String(b.last_consumed_at).localeCompare(String(a.last_consumed_at))
    return String(b.last_consumed_at).localeCompare(String(a.last_consumed_at)) // Mock：最近更新暂用同一字段
  })

  return (
    <div className="v2-block v2-index" data-testid="customer-index-card">
      <div className="v2-block-head">
        <div>
          <div className="v2-block-kicker">全部客户</div>
          <div className="v2-muted">{sorted.length} 位（Mock 化名）</div>
        </div>
        <button className="v2-link" onClick={onBack}>返回对话</button>
      </div>

      <div className="v2-search">
        <span>⌕</span>
        <input
          placeholder="搜索客户或别名"
          value={query}
          onChange={(e) => { setQuery(e.target.value); report({ query: e.target.value }) }}
        />
      </div>

      <div className="v2-filter-row">
        {FILTERS.map((f) => (
          <button key={f.key} className={`v2-chip ${filter === f.key ? 'active' : ''}`}
            onClick={() => { setFilter(f.key); report({ filter: f.key }) }}>
            {f.label}
          </button>
        ))}
        <select value={sort} onChange={(e) => { setSort(e.target.value); report({ sort: e.target.value }) }} aria-label="排序">
          {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>

      <div className="v2-index-list" ref={listRef} onScroll={() => report({ scrollPosition: listRef.current?.scrollTop || 0 })}>
        {sorted.map((c) => (
          <button key={c.id} className="v2-candidate" onClick={() => { report({ scrollPosition: listRef.current?.scrollTop || 0 }); onOpenCustomer(c) }}>
            <span className="v2-avatar">{c.display_name.slice(0, 1)}</span>
            <span className="v2-candidate-main">
              <strong>{c.display_name}{c.aliases.length > 0 && ` · ${c.aliases.join('、')}`}</strong>
              <span>最近 {c.last_consumed_at} · {c.service_type_count} 类服务</span>
            </span>
            <span className="v2-candidate-side">
              {c.unread_count > 0 && <em className="v2-new">新</em>}
              <span className="v2-chevron">›</span>
            </span>
          </button>
        ))}
        {sorted.length === 0 && <div className="v2-state">没有匹配的客户</div>}
      </div>
    </div>
  )
}
