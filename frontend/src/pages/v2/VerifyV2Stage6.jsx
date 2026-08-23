import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'
import AppHeader from '../../components/v1/AppHeader.jsx'

const CAPABILITIES = [
  ['sql_authoritative_rules', '三类 SQL 权威规则候选'],
  ['hard_exclusions_before_score', '硬排除先于评分'],
  ['top3_unique_customers', '今日主动事项按客户去重 Top3'],
  ['stable_rag_snapshot', '当前知识证据快照可追溯'],
  ['deterministic_safe_templates', '本地确定性安全话术与有限改写'],
  ['copy_only_no_send', '只复制，不提供外部发送'],
  ['read_and_handled_separate', '已读与已处理分离'],
  ['feedback_proposal_confirmation', '反馈提取内容确认前零权威写入'],
]

export default function VerifyV2Stage6() {
  const [data, setData] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api.getStage6Status(), api.getTodayRecommendations('top3')])
      .then(([status, today]) => { setData(status); setTasks(today) })
      .catch((failure) => setError(failure.message))
  }, [])
  const tests = data?.test_results || { status: '未验证' }
  return <div className="v1-app" style={{ overflow: 'auto' }}>
    <AppHeader />
    <div className="v1-content" style={{ padding: 16 }}>
      <div className="v1-panel">
        <h2>发财 V2 · 阶段6（推荐、话术和反馈）</h2>
        <p className="v1-hint">SQL 权威事实先执行硬排除与确定性评分，RAG 只提供当前知识证据。话术由本地安全模板生成，只允许店主复制，系统没有微信、短信或其他发送能力。</p>
        <div className="v2-preview-links">
          <Link className="v1-btn" to="/app/chat">打开店主主应用</Link>
          <Link className="v1-btn secondary" to="/verify/v2-stage-5">阶段5回归</Link>
        </div>
      </div>
      {error && <div className="v1-panel"><p className="v bad">接口未验证：{error}</p></div>}
      <div className="v1-panel">
        <h2>今日事项只读摘要</h2>
        <div className="v1-row"><span className="k">主动展示</span><span className="v">未处理 {tasks?.unresolved_count ?? '加载中'} · 未查看 {tasks?.unread_count ?? '加载中'} · 最多3位客户</span></div>
        {(tasks?.items || []).map((item) => <div className="v1-row" key={item.id}>
          <span className="k">{item.customer.display_name} · {item.type}</span>
          <span className="v">{item.degraded ? '降级' : '证据完整'} · {item.evidence.length} 条证据</span>
          <p className="v1-hint">{item.reason}</p>
        </div>)}
        {tasks && !tasks.items.length && <p className="v1-hint">当前没有今日推荐事项。正式库不会自动种虚构规则或推荐。</p>}
      </div>
      <div className="v1-panel">
        <h2>阶段6能力状态</h2>
        {CAPABILITIES.map(([key, label]) => <div className="v1-row" key={key}><span className="k">{label}</span><span className={`v ${data?.capabilities?.[key] ? 'ok' : 'bad'}`}>{data ? (data.capabilities[key] ? '已接通' : '未接通') : '加载中'}</span></div>)}
        <div className="v1-row"><span className="k">阶段7评测Runner、配置发布/回滚</span><span className="v ok">未开始</span></div>
        <div className="v1-row"><span className="k">真实模型 / 外部Embedding / 外部发送</span><span className="v ok">0 / 0 / 0</span></div>
      </div>
      <div className="v1-panel">
        <h2>Migration、测试与构建</h2>
        <div className="v1-row"><span className="k">当前 Migration</span><span className="v">{data?.migration || '加载中'}</span></div>
        <div className="v1-row"><span className="k">状态</span><span className={`v ${tests.status === '通过' ? 'ok' : 'bad'}`}>{tests.status}</span></div>
        <div className="v1-row"><span className="k">后端</span><span className="v">{tests.backend || '未验证'}</span></div>
        <div className="v1-row"><span className="k">前端</span><span className="v">{tests.frontend || '未验证'}</span></div>
        <div className="v1-row"><span className="k">构建</span><span className="v">{tests.build || '未验证'}</span></div>
      </div>
    </div>
  </div>
}
