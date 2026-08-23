// 阶段6今日事项：逐条打开才已读；查看、复制不等于处理；只允许复制，不提供发送。
import { useEffect, useRef, useState } from 'react'
import { computeTodayTaskCounts, groupTasks } from '../../lib/todayTasks.js'

const TYPE_LABELS = {
  product_repurchase: '产品复购关怀',
  service_follow_up: '服务回访',
  package_renewal: '套餐续费关怀',
}
const ACTIONS = [
  ['contacted', '已联系'], ['snoozed', '稍后'], ['repurchased', '已复购'],
  ['not_needed', '不需要'], ['unsuitable', '不适合'],
  ['do_not_recommend', '不再推荐'], ['cancelled', '取消'],
]

function evidenceLabel(item) {
  if (item.kind === 'transaction') return `账本购买 · ${item.occurred_on} · ${item.quantity} 件`
  if (item.kind === 'service_transaction') return `账本服务 · ${item.occurred_on}`
  if (item.kind === 'package_balance') return `权威余量 ${item.remaining_count} 次 · ${item.last_consumed_at || item.evidence_date}`
  if (item.document_id) return `资料 #${item.document_id} · v${item.knowledge_version} · ${item.source?.name || '已确认来源'}`
  return '结构化证据'
}

export default function RecommendationTodayTaskCard({
  tasks = [], groupLabels = {}, onRead, onHandle, onBack,
  onRecommendationAction, onRewrite, onCopy, savedScroll = 0, onScrollChange,
}) {
  const counts = computeTodayTaskCounts(tasks)
  const groups = groupTasks(tasks, groupLabels)
  const listRef = useRef(null)
  const [openId, setOpenId] = useState(null)
  const [feedback, setFeedback] = useState({})
  const [snoozeTimes, setSnoozeTimes] = useState({})
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (listRef.current && savedScroll) listRef.current.scrollTop = savedScroll
  }, [savedScroll])

  const openTask = (task) => {
    setOpenId((current) => current === task.id ? null : task.id)
    if (task.unread) onRead?.(task.id, task)
  }
  const run = async (callback, success) => {
    setNotice('')
    try {
      const result = await callback()
      setNotice(typeof success === 'function' ? success(result) : success)
    } catch (error) { setNotice(error.message) }
  }

  return <div className="v2-block v2-today" data-testid="today-task-card">
    <div className="v2-block-head">
      <div><div className="v2-block-kicker">今日事项</div><div className="v2-muted">未处理 {counts.unresolved_count} · 未查看 {counts.unread_count}</div></div>
      <button className="v2-link" onClick={onBack}>返回</button>
    </div>
    <p className="v2-hint">打开列表不会批量清除“新”；请逐条打开。查看或复制话术不等于已联系。</p>
    {notice && <div className="v2-inline-notice" role="status">{notice}</div>}
    <div className="v2-today-list" ref={listRef} onScroll={() => onScrollChange?.(listRef.current?.scrollTop || 0)} data-testid="today-list">
      {Object.entries(groups).map(([label, items]) => <div key={label} className="v2-today-group">
        <div className="v2-today-group-title">{label}</div>
        {items.map((task) => {
          const recommendation = task.recommendation
          const expanded = openId === task.id
          const standard = recommendation?.message_drafts?.find((item) => item.variant === 'standard')
          return <div key={task.id} className={`v2-today-item ${task.unread ? 'unread' : ''} ${expanded ? 'expanded' : ''}`} data-testid={`task-${task.id}`}>
            <button className="v2-today-item-main" onClick={() => openTask(task)} aria-expanded={expanded} aria-label={`${task.unread ? '新，' : ''}${task.customer_name}：${task.summary}`}>
              <span className="v2-today-dot" aria-hidden="true">{task.unread && <i className="v2-dot" />}</span>
              <span className="v2-today-main"><strong>{task.customer_name}{task.unread && <em className="v2-new">新</em>}</strong><span>{recommendation ? TYPE_LABELS[recommendation.type] : task.summary}</span><small>{task.date}</small></span>
            </button>
            {!recommendation && !task.handled_at && <button className="v2-btn secondary v2-today-handle" onClick={() => onHandle?.(task.id)}>处理</button>}
            {!recommendation && task.handled_at && <span className="v2-today-handled">已处理</span>}
            {recommendation && expanded && <div className="v2-recommendation-detail" data-testid={`recommendation-detail-${recommendation.id}`}>
              <div><strong>原因</strong><p>{recommendation.reason}</p></div>
              <div><strong>建议动作</strong><p>{recommendation.suggested_action}</p></div>
              <div><strong>证据</strong>{(recommendation.evidence || []).slice(0, 5).map((item, index) => <p className="v2-evidence" key={`${item.kind || item.document_id}-${index}`}>{evidenceLabel(item)}</p>)}</div>
              <div className={`v2-risk ${recommendation.degraded ? 'degraded' : 'safe'}`}>{recommendation.degraded ? '降级：仅使用结构化证据与安全基础提醒' : '证据链完整 · 资料仅作为不可信数据使用'}</div>
              {standard && <div className="v2-message-draft"><strong>可复制话术</strong><p>{standard.content}</p><div className="v2-action-row">
                <button className="v2-btn" onClick={() => run(() => onCopy?.(task, standard), '已复制；未发送')}>复制话术</button>
                <button className="v2-btn secondary" onClick={() => run(() => onRewrite?.(task, 'shorter'), '已生成更短版本')}>短一点</button>
                <button className="v2-btn secondary" onClick={() => run(() => onRewrite?.(task, 'no_purchase'), '已生成不提购买版本')}>不提购买</button>
              </div></div>}
              {(recommendation.message_drafts || []).filter((item) => item.variant !== 'standard').map((draft) => <div className="v2-message-draft compact" key={draft.id}><small>{draft.variant === 'shorter' ? '短一点' : '不提购买'}</small><p>{draft.content}</p><button className="v2-btn secondary" onClick={() => run(() => onCopy?.(task, draft), '已复制；未发送')}>复制此版本</button></div>)}
              <label className="v2-feedback-label">反馈原文（AI不准确时必填）<textarea value={feedback[task.id] || ''} onChange={(event) => setFeedback((value) => ({ ...value, [task.id]: event.target.value }))} placeholder="例如：客户说偏好清爽，10天后再问。提取内容仍需确认。" /></label>
              <label className="v2-feedback-label">稍后处理时间（不填则明天10:00；原文含日期时以确认卡为准）<input type="datetime-local" value={snoozeTimes[task.id] || ''} onChange={(event) => setSnoozeTimes((value) => ({ ...value, [task.id]: event.target.value }))} /></label>
              <div className="v2-action-row v2-feedback-actions">{ACTIONS.map(([action, labelText]) => <button key={action} className="v2-btn secondary" onClick={() => run(
                () => onRecommendationAction?.(task, action, feedback[task.id] || '', snoozeTimes[task.id] || ''),
                (result) => result?.proposal ? '已生成待确认事项，确认前不写入提醒或客户事实' : action === 'snoozed' ? '已设置稍后处理' : `已记录：${labelText}`,
              )}>{labelText}</button>)}</div>
              <button className="v2-btn secondary" onClick={() => run(() => {
                const text = (feedback[task.id] || '').trim()
                if (!text) throw new Error('请先填写AI不准确的具体说明')
                return onRecommendationAction?.(task, 'ai_inaccurate', text, '')
              }, '已记录：AI不准确；不会自动训练或改变事项状态')}>AI不准确</button>
              <p className="v2-hint">系统未建设微信、短信或其他发送能力。反馈状态更新不调用模型；从原文提取的事实或日期会先生成确认卡。</p>
            </div>}
          </div>
        })}
      </div>)}
      {tasks.length === 0 && <div className="v2-state">今日没有待处理事项</div>}
    </div>
  </div>
}
