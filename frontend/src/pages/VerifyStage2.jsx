import { useState } from 'react'
import { api, formatPrice } from '../api.js'

const ACTION_TYPE_LABEL = {
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
const SERVICE_STATUS_LABEL = {
  exact: '精确',
  fuzzy: '近似建议',
  ambiguous: '多个候选',
  not_found: '未匹配',
}

// PRD 7.4 的 10 条测试表达
const TEST_EXPRESSIONS = [
  '阿珍今天买了一盒面膜。',
  '小美今天脱毛一次。',
  '王姐今天肩颈按摩1次。',
  '王姐今天买了面部清洁5次。',
  '给我瞅瞅珍姐现在还有什么服务。',
  '小绿做了一次脸。',
  '李阿姨买了一个面霜。',
  '王姐来店里本次做了面部清洁，清痘，做身体，本次额外买了面霜。',
  '天天的肩颈卡今天又用了一次。',
  '小普好几天没来了，你给我看看，他还有卡吗，有啥卡，还剩几次。',
]

export default function VerifyStage2() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const run = async (input) => {
    const value = (input ?? text).trim()
    if (!value) {
      setError('请输入要解析的内容')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await api.interpret(value)
      setResult(data)
      if (data.error) setError(data.error)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page">
      <h1>阶段2 验证页</h1>
      <p className="subtitle">自然语言 → 结构化建议（本阶段只解析，不写入数据库）</p>

      <section className="card">
        <textarea
          className="input-area"
          placeholder="输入店主的自然语言描述，例如：阿珍今天买了一盒面膜。"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
        />
        <div className="row-actions" style={{ marginTop: 10 }}>
          <button onClick={() => run()} disabled={loading}>
            {loading ? '解析中…' : '解析'}
          </button>
        </div>

        <div className="preset-list">
          <p className="muted">点击测试表达直接解析：</p>
          {TEST_EXPRESSIONS.map((expr, i) => (
            <button key={i} className="preset" onClick={() => run(expr)} disabled={loading}>
              {i + 1}. {expr}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div className="error-banner">{error}</div>
      )}

      {result && !result.error && <ResultView result={result} />}
    </main>
  )
}

function ResultView({ result }) {
  const cm = result.customer_match || {}
  return (
    <section className="card">
      <div className="result-header">
        <h2>解析结果</h2>
        <span className="muted">提示词版本 v{result.prompt_version}</span>
      </div>

      <p className="muted">原始输入：{result.original_input}</p>

      <div className="block">
        <strong>客户识别：</strong>
        <span className={`tag tag-customer`}>{CUSTOMER_STATUS_LABEL[cm.status] || cm.status}</span>
        <span className="muted"> “{result.customer_query || '（未识别）'}”</span>
      </div>

      {cm.candidates && cm.candidates.length > 0 && (
        <div className="block">
          <span className="muted">候选客户：</span>
          {cm.candidates.map((c) => (
            <div key={c.id} className="candidate">
              {c.display_name}
              {c.aliases && c.aliases.length > 0 && `（${c.aliases.join('、')}）`}
              <span className="muted"> 相似度 {Math.round(c.score * 100)}%</span>
            </div>
          ))}
          {cm.status === 'ambiguous' && (
            <p className="hint">有多个近似客户，本次为您展示前3位，请问有您咨询的客户吗？</p>
          )}
        </div>
      )}

      {cm.new_customer_name && (
        <div className="block">
          <span className="tag tag-customer">新客户</span>
          <span className="muted"> 系统未找到“{cm.new_customer_name}”，确认时会询问是否新增。</span>
        </div>
      )}

      <div className="block">
        <strong>识别出的操作（{result.actions.length} 项）：</strong>
        {result.actions.length === 0 && <p className="muted">（无）</p>}
        <ul className="list">
          {result.actions.map((a, i) => (
            <li key={i} className="list-item column">
              <div>
                <span className="tag tag-ledger">{ACTION_TYPE_LABEL[a.type] || a.type}</span>
                {a.service_name && <strong> 服务：{a.service_name}</strong>}
                {a.product_name && <strong> 商品：{a.product_name}</strong>}
              </div>
              <div className="muted">
                数量 {a.quantity ?? '—'}
                {a.total_count != null && ` · 总次数 ${a.total_count}`}
                {a.price_cents != null && ` · 价格 ${formatPrice(a.price_cents)} 元`}
                {a.purchased_on && ` · 日期 ${a.purchased_on}`}
              </div>
              {a.service_match && (
                <ServiceMatchInfo match={a.service_match} />
              )}
            </li>
          ))}
        </ul>
      </div>

      {result.needs_clarification && result.clarification_question && (
        <div className="block">
          <span className="tag tag-package">需要澄清</span>
          <p className="hint">系统提问：{result.clarification_question}</p>
        </div>
      )}

      <div className="block">
        <button disabled title="本阶段不写入">
          确认写入（本阶段不开放）
        </button>
        <p className="hint">阶段2只验证“解析”，确认写入功能将在阶段3开放。</p>
      </div>
    </section>
  )
}

function ServiceMatchInfo({ match }) {
  const status = SERVICE_STATUS_LABEL[match.status] || match.status
  if (match.status === 'exact' && match.candidates[0]) {
    return (
      <div className="muted">
        服务匹配：<span className="tag tag-service">{match.candidates[0].name}</span>（精确）
      </div>
    )
  }
  if (match.status === 'fuzzy' && match.candidates[0]) {
    return (
      <div className="muted">
        服务匹配建议：<span className="tag tag-service">{match.candidates[0].name}</span>（{status}，确认页可改选）
      </div>
    )
  }
  if (match.status === 'ambiguous') {
    return (
      <div className="muted">
        服务匹配：有 {match.candidates.length} 个候选（{match.candidates.map((c) => c.name).join('、')}），需人工选择
      </div>
    )
  }
  return <div className="muted">服务匹配：未找到，需澄清或选择已有服务</div>
}
