import { useState } from 'react'
import AppHeader from '../../components/v1/AppHeader.jsx'

const V1_CAPABILITIES = [
  '客户/服务/套餐/账本 CRUD、软删除与回收站',
  '权威余额：opening_used_count + 未删除核销记录',
  '自然语言记账 + 聊天内确认卡 + 幂等 + 整组事务',
  '客户读模型（最后消费/概览/服务详情三级）',
  '提示词版本管理（保存/激活/回退）',
]

const V2_DIFF = [
  ['租户与身份', '新增 Tenant/User(owner/admin)/Invite'],
  ['客户事实', '新增 CustomerFact（证据/置信度/敏感级别/版本）'],
  ['产品实体', '新增 Product/ProductAlias（品牌+名称+规格）'],
  ['知识/RAG', '新增知识版本 + Embedding + 混合检索'],
  ['推荐', '新增复购/回访/续卡 + 强制过滤 + 话术'],
  ['多日会话', '新增 Thread/Session/PendingAction/绝对日期'],
  ['语音', '新增 SpeechToTextAdapter（转写先可见可改）'],
  ['角色权限', 'owner + admin RBAC（后端强制）'],
  ['AI 治理', '草稿→测评→发布→回滚'],
  ['UI Block', 'contracts/ui-block.schema.json 六类 Block'],
]

const ADAPTERS = [
  ['语音识别 SpeechToText', '浏览器 Web Speech API（原型）→ 云语音（阿里/腾讯，需确认）→ OpenAI Whisper（备选）'],
  ['向量 Embedding', '本地 bge-small-zh（MVP 推荐）→ 智谱/阿里云 embedding（云候选）；DeepSeek 不提供 Embedding'],
]

const RISKS = [
  'V1 无 Alembic，V2 需引入显式 Migration',
  '现有表缺 tenant_id，需回填默认租户',
  'product_name 自由文本需迁移为 Product 草稿',
  '只增表不重命名/删除 V1 权威字段，回滚不破坏账本',
]

export default function VerifyV2Stage0() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const runVerify = async () => {
    setLoading(true)
    setError('')
    setResults(null)
    try {
      const resp = await fetch('/api/v2/stage0/verify-model', { method: 'POST' })
      setResults(await resp.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>发财 V2 · 阶段0（代码审计与模型验证）</h2>
          <p className="v1-hint">本轮只做审计和验证，不改业务数据、不开发后续功能。</p>
        </div>

        <div className="v1-panel">
          <h2>DeepSeek 模型真实验证</h2>
          <div style={{ marginBottom: 10 }}>
            <button className="v1-btn" onClick={runVerify} disabled={loading}>
              {loading ? '验证中…' : '运行模型验证'}
            </button>
          </div>
          {error && <div className="v1-error-banner">{error}</div>}
          {results && !results.configured && (
            <div className="v1-error-banner">未配置 API Key（backend/.env）</div>
          )}
          {results && results.configured && (
            <>
              <div className="v1-row"><span className="k">模型</span><span className="v">{results.model}</span></div>
              <div className="v1-row"><span className="k">接口</span><span className="v">{results.base}</span></div>
              {results.results.map((r, i) => (
                <div key={i} className="v1-row">
                  <span className="k">{r.name}</span>
                  <span className={`v ${r.ok ? 'ok' : 'bad'}`}>{r.ok ? '✅ 通过' : '❌ 失败'}</span>
                </div>
              ))}
              {results.results.map((r, i) => (
                <p key={i} className="v1-hint" style={{ marginTop: 4 }}>{r.detail}</p>
              ))}
            </>
          )}
        </div>

        <div className="v1-panel">
          <h2>V1 能力清单（保留底座）</h2>
          {V1_CAPABILITIES.map((c, i) => <div key={i} className="v1-row"><span className="k">{c}</span><span className="v ok">已具备</span></div>)}
        </div>

        <div className="v1-panel">
          <h2>V2 差异矩阵（新增/变化）</h2>
          {V2_DIFF.map(([k, v], i) => (
            <div key={i} className="v1-row">
              <span className="k">{k}</span>
              <span className="v" style={{ fontSize: 13 }}>{v}</span>
            </div>
          ))}
        </div>

        <div className="v1-panel">
          <h2>适配器候选与取舍</h2>
          {ADAPTERS.map(([k, v], i) => (
            <div key={i} className="v1-row" style={{ alignItems: 'flex-start' }}>
              <span className="k">{k}</span>
              <span className="v" style={{ fontSize: 13, textAlign: 'right' }}>{v}</span>
            </div>
          ))}
        </div>

        <div className="v1-panel">
          <h2>数据库迁移风险</h2>
          {RISKS.map((r, i) => <div key={i} className="v1-row"><span className="k" style={{ fontSize: 13 }}>{i + 1}. {r}</span></div>)}
        </div>

        <div className="v1-panel">
          <h2>阶段1 实施计划（预告）</h2>
          <p className="v1-hint">
            引入 Alembic → Tenant/User/Invite → CustomerFact/Product/会话/推荐等新表 → owner/admin RBAC → product_name 迁移 → V1 账本回归。
          </p>
        </div>
      </div>
    </div>
  )
}
