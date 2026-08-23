import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'
import AppHeader from '../../components/v1/AppHeader.jsx'
import ProductMatchCard from '../../components/v2/ProductMatchCard.jsx'

const CAPABILITIES = [
  ['fact_evidence_confirmation', '客户事实候选、原话证据与确认后写入'],
  ['fact_versioning_without_overwrite', '冲突事实保留旧版本并建立 supersedes 关系'],
  ['sensitive_fact_separation', '敏感/不适事实在确认卡明确单列'],
  ['product_exact_alias_fuzzy_embedding_candidates', '产品 canonical / alias / fuzzy / 名称语义候选'],
  ['new_product_purchase_atomic', '新产品草稿与购买同事务'],
  ['product_merge_proposal', '重复产品合并经统一 Proposal'],
  ['knowledge_status_visible', 'draft / active 与资料待补充状态可见'],
]

export default function VerifyV2Stage4() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [match, setMatch] = useState(null)

  useEffect(() => {
    Promise.all([api.getStage4Status(), api.getProducts()])
      .then(([status, products]) => setData({ status, products }))
      .catch((failure) => setError(failure.message))
  }, [])

  const inspect = async () => {
    setError('')
    try { setMatch(await api.resolveProduct({ query })) } catch (failure) { setError(failure.message) }
  }
  const tests = data?.status?.test_results || { status: '未验证' }
  const integrity = typeof tests.data_integrity === 'string'
    ? tests.data_integrity
    : tests.data_integrity
      ? `${tests.data_integrity.before} → ${tests.data_integrity.after}`
      : '未验证'

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>发财 V2 · 阶段4（客户事实和产品实体）</h2>
          <p className="v1-hint">真实客户事实版本、产品实体匹配、草稿/合并和统一确认已接通。本阶段没有建设知识文档索引、RAG 或推荐。</p>
          <div className="v2-preview-links">
            <Link className="v1-btn" to="/app/chat">主对话验收</Link>
            <Link className="v1-btn secondary" to="/app/customers">客户档案验收</Link>
            <Link className="v1-btn secondary" to="/app/manage">产品管理验收</Link>
          </div>
        </div>

        {error && <div className="v1-panel"><p className="v bad">接口未验证：{error}</p></div>}

        <div className="v1-panel">
          <h2>产品匹配试验台（只读，不写入）</h2>
          <div className="v2-edit-inline">
            <label>产品名称<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入标准名、别名或近似名称" /></label>
            <button className="v1-btn" disabled={!query.trim()} onClick={inspect}>检查候选</button>
          </div>
          {match && <ProductMatchCard match={match} />}
          <p className="v1-hint">名称语义候选是阶段4本地产品实体匹配层，不写 EmbeddingRecord，也不调用 RAG。</p>
        </div>

        <div className="v1-panel">
          <h2>当前产品实体</h2>
          {data?.products?.length ? data.products.map((product) => (
            <div className="v1-row" key={product.id}>
              <span className="k">#{product.id} · {product.canonical_name}</span>
              <span className="v">{product.lifecycle_status} · {product.knowledge_status} · 购买{product.purchase_count}次</span>
            </div>
          )) : <p className="v1-hint">暂无产品实体；历史 product_name 会由 Migration 保留并关联到草稿。</p>}
        </div>

        <div className="v1-panel">
          <h2>阶段4能力状态</h2>
          {CAPABILITIES.map(([key, label]) => (
            <div className="v1-row" key={key}>
              <span className="k">{label}</span>
              <span className={`v ${data?.status?.capabilities?.[key] ? 'ok' : 'bad'}`}>{data ? (data.status.capabilities[key] ? '已接通' : '未接通') : '加载中'}</span>
            </div>
          ))}
          <div className="v1-row"><span className="k">RAG / 知识 Embedding 索引</span><span className="v ok">未建设（阶段5边界）</span></div>
        </div>

        <div className="v1-panel">
          <h2>Migration、测试与构建</h2>
          <div className="v1-row"><span className="k">当前 Migration</span><span className="v">{data?.status?.migration || '加载中'}</span></div>
          <div className="v1-row"><span className="k">状态</span><span className={`v ${tests.status === '通过' ? 'ok' : 'bad'}`}>{tests.status || '未验证'}</span></div>
          <div className="v1-row"><span className="k">后端</span><span className="v">{tests.backend || '未验证'}</span></div>
          <div className="v1-row"><span className="k">前端</span><span className="v">{tests.frontend || '未验证'}</span></div>
          <div className="v1-row"><span className="k">生产构建</span><span className="v">{tests.build || '未验证'}</span></div>
          <div className="v1-row"><span className="k">迁移与原数据</span><span className="v">{tests.migration_cycle || '未验证'} · {integrity}</span></div>
        </div>
      </div>
    </div>
  )
}
