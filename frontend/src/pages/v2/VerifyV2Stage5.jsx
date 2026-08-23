import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'
import AppHeader from '../../components/v1/AppHeader.jsx'

const CAPABILITIES = [
  ['proposal_confirmation_only', '知识候选仅生成 Proposal，确认后事务发布'],
  ['knowledge_versioning', '当前版本生效，旧版本保留可追溯'],
  ['confirmed_current_active_filter', 'confirmed / current / active 强过滤'],
  ['local_deterministic_embedding', '本地确定性、可版本化 Embedding'],
  ['embedding_checksum_idempotency', 'checksum 不变不重复生成'],
  ['dimension_isolation', '索引维度不混用'],
  ['hybrid_retrieval', '实体精确 > 关键词别名 > 本地向量'],
  ['tenant_metadata_filter', 'tenant 与实体 metadata 强隔离'],
  ['pii_injection_script_gate', 'PII / 提示注入 / 脚本门禁'],
  ['stable_evidence_only', '仅返回稳定证据，不生成推荐或话术'],
]

export default function VerifyV2Stage5() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [evidence, setEvidence] = useState(null)

  useEffect(() => {
    Promise.all([api.getStage5Status(), api.getOwnerKnowledge()])
      .then(([status, knowledge]) => setData({ status, knowledge }))
      .catch((failure) => setError(failure.message))
  }, [])

  const retrieve = async () => {
    setError('')
    try { setEvidence(await api.retrieveKnowledge({ query, limit: 5 })) }
    catch (failure) { setError(failure.message) }
  }
  const status = data?.status
  const tests = status?.test_results || { status: '未验证' }
  return <div className="v1-app" style={{ overflow: 'auto' }}>
    <AppHeader />
    <div className="v1-content" style={{ padding: 16 }}>
      <div className="v1-panel">
        <h2>发财 V2 · 阶段5（RAG 知识链路）</h2>
        <p className="v1-hint">已确认的产品/服务知识经过本地确定性索引进入证据检索。知识是不可信数据，只能提供证据，不能改变权限或生成推荐。</p>
        <div className="v2-preview-links">
          <Link className="v1-btn" to="/app/manage">店主只读状态</Link>
          <Link className="v1-btn secondary" to="/admin/knowledge">管理员知识管理</Link>
          <Link className="v1-btn secondary" to="/verify/v2-stage-4">阶段4回归</Link>
        </div>
      </div>

      {error && <div className="v1-panel"><p className="v bad">接口未验证：{error}</p></div>}

      <div className="v1-panel">
        <h2>只读证据检索</h2>
        <div className="v2-edit-inline">
          <label>知识查询<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入产品、服务、别名或知识关键词" /></label>
          <button className="v1-btn" disabled={!query.trim()} onClick={retrieve}>检索证据</button>
        </div>
        {evidence?.evidence?.map((item) => <div className="v1-row" key={item.document_id}>
          <span className="k">文档 #{item.document_id} · v{item.knowledge_version} · {item.source.name}</span>
          <span className="v">{item.match} · {item.score}</span>
          <p className="v1-hint">{item.snippet}</p>
        </div>)}
        {evidence && !evidence.evidence.length && <p className="v1-hint">知识不足：没有符合当前 tenant、实体、确认、状态和版本过滤的证据。</p>}
      </div>

      <div className="v1-panel">
        <h2>当前知识状态</h2>
        <div className="v1-row"><span className="k">当前已发布文档</span><span className="v">{status?.counts?.active_documents ?? '加载中'}</span></div>
        <div className="v1-row"><span className="k">本地索引</span><span className="v">{status?.owner_status?.embedding?.indexed ?? '加载中'} 已索引 / {status?.owner_status?.embedding?.failed ?? '加载中'} 失败</span></div>
        <div className="v1-row"><span className="k">Embedding 运行时</span><span className="v">{status ? `${status.runtime.embedding_provider} · ${status.runtime.embedding_model} · ${status.runtime.dimension}维` : '加载中'}</span></div>
        <div className="v1-row"><span className="k">外部服务/真实模型</span><span className="v ok">未调用 · 无网络依赖</span></div>
        {data?.knowledge?.map((item) => <div className="v1-row" key={item.document_id}>
          <span className="k">{item.entity_type} #{item.entity_id} · v{item.knowledge_version}</span>
          <span className="v">{item.source_name} · {item.index_status}</span>
        </div>)}
      </div>

      <div className="v1-panel">
        <h2>阶段5能力状态</h2>
        {CAPABILITIES.map(([key, label]) => <div className="v1-row" key={key}>
          <span className="k">{label}</span>
          <span className={`v ${status?.capabilities?.[key] ? 'ok' : 'bad'}`}>{status ? (status.capabilities[key] ? '已接通' : '未接通') : '加载中'}</span>
        </div>)}
        <div className="v1-row"><span className="k">阶段6推荐、Top3、提醒、话术、反馈</span><span className="v ok">未开始</span></div>
      </div>

      <div className="v1-panel">
        <h2>Migration、测试与构建</h2>
        <div className="v1-row"><span className="k">当前 Migration</span><span className="v">{status?.migration || '加载中'}</span></div>
        <div className="v1-row"><span className="k">状态</span><span className={`v ${tests.status === '通过' ? 'ok' : 'bad'}`}>{tests.status}</span></div>
        <div className="v1-row"><span className="k">后端</span><span className="v">{tests.backend || '未验证'}</span></div>
        <div className="v1-row"><span className="k">前端</span><span className="v">{tests.frontend || '未验证'}</span></div>
        <div className="v1-row"><span className="k">构建</span><span className="v">{tests.build || '未验证'}</span></div>
      </div>
    </div>
  </div>
}
