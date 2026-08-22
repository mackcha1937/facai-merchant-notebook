import { useState } from 'react'
import { Link } from 'react-router-dom'
import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'
import AgentProposalCard from '../../components/v1/AgentProposalCard.jsx'
import { api } from '../../api.js'

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
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async (text) => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await api.interpret(text)
      setResult(data)
      if (data.error) setError(data.error)
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
          <h2>阶段2 · 自然语言解析（仅预览）</h2>
          <p className="v1-hint">点击下方测试表达，查看解析结果；本阶段不写入数据库。</p>
          <div style={{ display: 'grid', gap: 6, marginTop: 10 }}>
            {TEST_EXPRESSIONS.map((expr, i) => (
              <button key={i} className="v1-test-btn" onClick={() => run(expr)} disabled={loading}>
                {i + 1}. {expr}
              </button>
            ))}
          </div>
          <p className="v1-hint" style={{ marginTop: 10 }}>
            <Link to="/settings/prompt">系统提示词管理 →</Link>
          </p>
        </div>

        {error && <div className="v1-error-banner">{error}</div>}
        {loading && <div className="v1-state"><span className="v1-spinner" /></div>}
        {result && !result.error && (
          <div className="v1-confirm-message">
            <AgentProposalCard proposal={result} />
          </div>
        )}
      </div>
      <BottomNavigation />
    </div>
  )
}
