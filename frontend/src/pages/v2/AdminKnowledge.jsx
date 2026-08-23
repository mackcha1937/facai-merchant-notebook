import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'

const key = (prefix) => `${prefix}-${globalThis.crypto?.randomUUID?.() || Date.now()}`

export default function AdminKnowledge() {
  const [rows, setRows] = useState([])
  const [products, setProducts] = useState([])
  const [services, setServices] = useState([])
  const [draft, setDraft] = useState({ entity_type: 'product', entity_id: '', title: '', content: '', source_name: '店主确认资料' })
  const [pending, setPending] = useState(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const refresh = useCallback(() => Promise.all([api.getAdminKnowledge(), api.getProducts(), api.getServices()])
    .then(([knowledge, productRows, serviceRows]) => { setRows(knowledge); setProducts(productRows); setServices(serviceRows); setError('') })
    .catch((failure) => setError(failure.message)), [])
  useEffect(() => { refresh() }, [refresh])
  const entities = (draft.entity_type === 'product' ? products : services)
    .filter((entity) => draft.entity_type === 'product' ? entity.lifecycle_status === 'active' : entity.status === 'active')

  const create = async () => {
    setError(''); setNotice('')
    try {
      const proposal = await api.createAdminKnowledgeProposal({
        ...draft, entity_id: Number(draft.entity_id), source_type: 'owner_confirmed', aliases: [],
        request_id: key('knowledge-request'), idempotency_key: key('knowledge-idempotency'),
      })
      setPending(proposal.proposal); setNotice('已生成统一确认卡；当前尚未发布知识。')
    } catch (failure) { setError(failure.message) }
  }
  const confirm = async () => {
    try {
      await api.confirmAdminKnowledgeProposal(pending.id, { idempotency_key: key('knowledge-confirm'), device_id: 'admin-web', data_version: pending.data_version })
      setPending(null); setNotice('知识已确认发布并建立本地索引。'); refresh()
    } catch (failure) { setError(failure.message) }
  }
  const withdraw = async (row) => {
    try {
      const proposal = await api.createAdminKnowledgeWithdrawProposal({
        entity_type: row.entity_type, entity_id: row.entity_id, reason: '管理员人工撤回当前资料',
        request_id: key('withdraw-request'), idempotency_key: key('withdraw-idempotency'),
      })
      setPending(proposal.proposal); setNotice('已生成撤回确认卡；确认前当前知识仍有效。')
    } catch (failure) { setError(failure.message) }
  }
  const reindex = async (row) => {
    try { const result = await api.reindexKnowledge(row.entity_type, row.entity_id); setNotice(`索引处理：${result.status}`); refresh() }
    catch (failure) { setError(failure.message) }
  }

  return <main className="page" style={{ maxWidth: 980 }}>
    <div className="card">
      <h1>阶段5 · 管理员知识管理</h1>
      <p className="hint">草稿只生成 Proposal；发布和撤回需统一确认。仅使用店主确认资料或已发布规范，不接受模型常识。</p>
      <p><Link to="/verify/v2-stage-5">← 返回阶段5验收页</Link></p>
    </div>
    {error && <div className="error-banner">{error}</div>}
    {notice && <div className="notice-banner">{notice}</div>}
    <section className="card">
      <h2>新建知识草稿</h2>
      <div className="edit-grid">
        <label>实体类型<select value={draft.entity_type} onChange={(event) => setDraft({ ...draft, entity_type: event.target.value, entity_id: '' })}><option value="product">产品</option><option value="service">服务</option></select></label>
        <label>实体<select value={draft.entity_id} onChange={(event) => setDraft({ ...draft, entity_id: event.target.value })}><option value="">请选择已启用实体</option>{entities.map((entity) => <option key={entity.id} value={entity.id}>{entity.canonical_name || entity.name}</option>)}</select></label>
        <label>标题<input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
        <label>来源<input value={draft.source_name} onChange={(event) => setDraft({ ...draft, source_name: event.target.value })} /></label>
        <label>内容<textarea rows="7" value={draft.content} onChange={(event) => setDraft({ ...draft, content: event.target.value })} /></label>
      </div>
      <button disabled={!draft.entity_id || !draft.title.trim() || !draft.content.trim()} onClick={create}>生成发布确认卡</button>
    </section>
    {pending && <section className="card" data-testid="knowledge-confirm-card">
      <h2>{pending.title}</h2><p>{pending.changes_summary}</p>
      <p className="hint">确认前 KnowledgeVersion、KnowledgeDocument、Chunk、EmbeddingRecord 均不会写入。</p>
      <button onClick={confirm}>管理员确认并发布</button>
    </section>}
    <section className="card">
      <h2>版本、来源与索引</h2>
      {rows.map((row) => <div className="list-item column" key={row.document_id}>
        <div className="list-item-main"><strong>{row.entity_type} #{row.entity_id} · v{row.knowledge_version}</strong><span className={`tag ${row.active ? 'tag-active' : 'tag-inactive'}`}>{row.status}</span></div>
        <div className="hint">来源：{row.source_name} · checksum：{row.checksum?.slice(0, 12)}… · Embedding：{row.index_status}{row.embedding ? ` / ${row.embedding.provider} / ${row.embedding.model} / ${row.embedding.dimension}维` : ''}</div>
        {row.active && <div className="row-actions"><button onClick={() => reindex(row)}>重建本地索引</button><button className="danger" onClick={() => withdraw(row)}>生成撤回确认卡</button></div>}
      </div>)}
      {!rows.length && <p className="empty">暂无知识版本。</p>}
    </section>
  </main>
}
