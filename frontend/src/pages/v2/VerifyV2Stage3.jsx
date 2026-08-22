import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'
import AppHeader from '../../components/v1/AppHeader.jsx'

const CAPABILITIES = [
  ['single_main_thread', '每个 tenant＋owner 只有一个持续主 Thread'],
  ['daily_sessions', 'Asia/Shanghai 按自然日创建 Session 与日期分隔'],
  ['cursor_history', '历史消息游标分页与刷新恢复'],
  ['pending_recovery', '跨日 PendingAction 继续、放弃、过期与重新生成'],
  ['absolute_relative_dates', '相对日期首次解析后固定为绝对日期'],
  ['unified_proposal', '一次输入最多一张统一写入确认卡'],
  ['strong_idempotency', '重复点击、请求与网络重试幂等'],
  ['transactional_batch', '多项操作同事务成功或整组回滚'],
  ['cross_device_conflict', '手机/Web 并发确认仅一个成功并返回冲突回执'],
  ['latest_authoritative_cards', '历史客户卡重新展开读取最新权威余额'],
]

export default function VerifyV2Stage3() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.getStage3Status(),
      api.getMainThread(),
      api.getChatHistory({ limit: 100 }),
      api.getPendingActions(),
    ]).then(([status, thread, history, pending]) => {
      setData({ status, thread, history, pending })
    }).catch((failure) => setError(failure.message))
  }, [])

  const sessions = data ? [...new Set(data.history.messages.map((message) => message.session_date))] : []
  const tests = data?.status?.test_results || { status: '未验证' }
  const integrity = tests.data_integrity || null

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>发财 V2 · 阶段3（多日会话与统一 Proposal）</h2>
          <p className="v1-hint">真实会话、数据库、事务、幂等与冲突闭环；受控阶段3解析器不调用收费模型。客户事实、产品 AI 识别、RAG、Embedding、推荐与真实语音未开始。</p>
          <div className="v2-preview-links">
            <Link className="v1-btn" to="/app/chat">主对话</Link>
            <Link className="v1-btn secondary" to="/app/customers">全部客户</Link>
            <Link className="v1-btn secondary" to="/app/manage">管理与设置</Link>
          </div>
        </div>

        {error && <div className="v1-panel"><p className="v bad">接口未验证：{error}</p></div>}

        <div className="v1-panel">
          <h2>主 Thread 与按日 Session</h2>
          <div className="v1-row"><span className="k">主 Thread</span><span className="v">{data ? `#${data.thread.id}` : '加载中'}</span></div>
          <div className="v1-row"><span className="k">当前 Session</span><span className="v">{data?.thread?.session?.session_date || '加载中'} · Asia/Shanghai</span></div>
          <div className="v1-row"><span className="k">历史日期分隔</span><span className="v">{sessions.length ? sessions.join(' / ') : '暂无历史消息'}</span></div>
          <div className="v1-row"><span className="k">历史消息 / 待办</span><span className="v">{data ? `${data.history.messages.length} / ${data.pending.items.length}` : '加载中'}</span></div>
        </div>

        <div className="v1-panel">
          <h2>PendingAction 与固定日期</h2>
          {data?.pending?.items?.length ? data.pending.items.map((item) => (
            <div className="v1-row" key={item.id}>
              <span className="k">#{item.id} · {item.status}</span>
              <span className="v">{item.proposal.changes_summary} · {item.proposal.absolute_date} · {item.proposal.resolved_absolute_dates?.occurred_on?.timezone}</span>
            </div>
          )) : <p className="v1-hint">当前没有未完成确认；可在主对话输入化名、已有服务、次数和日期生成。</p>}
        </div>

        <div className="v1-panel">
          <h2>阶段3能力状态</h2>
          {CAPABILITIES.map(([key, label]) => (
            <div className="v1-row" key={key}>
              <span className="k">{label}</span>
              <span className={`v ${data?.status?.capabilities?.[key] ? 'ok' : 'bad'}`}>{data ? (data.status.capabilities[key] ? '已接通' : '未接通') : '加载中'}</span>
            </div>
          ))}
        </div>

        <div className="v1-panel">
          <h2>Migration 与 V1 数据完整性</h2>
          <div className="v1-row"><span className="k">当前 Migration</span><span className="v">{data?.status?.migration || '加载中'}</span></div>
          <div className="v1-row"><span className="k">升级 / 降级 / 再升级</span><span className="v">{tests.migration_cycle || '未验证'}</span></div>
          <div className="v1-row"><span className="k">迁移前后客户 / 套餐 / 账本 / 剩余次数</span><span className="v">{integrity ? `${integrity.before} → ${integrity.after}` : '未验证'}</span></div>
        </div>

        <div className="v1-panel">
          <h2>自动测试与构建</h2>
          <div className="v1-row"><span className="k">状态</span><span className={`v ${tests.status === '通过' ? 'ok' : 'bad'}`}>{tests.status || '未验证'}</span></div>
          <div className="v1-row"><span className="k">后端</span><span className="v">{tests.backend || '未验证'}</span></div>
          <div className="v1-row"><span className="k">前端</span><span className="v">{tests.frontend || '未验证'}</span></div>
          <div className="v1-row"><span className="k">生产构建</span><span className="v">{tests.build || '未验证'}</span></div>
          <div className="v1-row"><span className="k">敏感信息扫描</span><span className="v">{tests.sensitive_scan || '未验证'}</span></div>
          <p className="v1-hint">本页只展示实际记录到交付报告的检查；没有执行的项目明确标记“未验证”。</p>
        </div>
      </div>
    </div>
  )
}
