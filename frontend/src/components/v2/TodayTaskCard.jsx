// TodayTaskCard：按 建议跟进/待确认/资料待补充/冲突 分组。
// - 打开总列表不清除全部红点；
// - 只有成功打开某一条后才更新该条 read_at；
// - 查看不等于处理；处理后未处理数才下降；
// - 返回时恢复原列表位置（保存 scrollTop）。
import { useEffect, useRef } from 'react'
import { computeTodayTaskCounts, groupTasks } from '../../lib/todayTasks.js'

export default function TodayTaskCard({ tasks = [], groupLabels = {}, onRead, onHandle, onBack, savedScroll = 0, onScrollChange }) {
  const counts = computeTodayTaskCounts(tasks)
  const groups = groupTasks(tasks, groupLabels)
  const listRef = useRef(null)

  useEffect(() => {
    if (listRef.current && savedScroll) {
      listRef.current.scrollTop = savedScroll
    }
  }, [savedScroll])

  const handleScroll = () => {
    onScrollChange?.(listRef.current?.scrollTop || 0)
  }

  return (
    <div className="v2-block v2-today" data-testid="today-task-card">
      <div className="v2-block-head">
        <div>
          <div className="v2-block-kicker">今日事项</div>
          <div className="v2-muted">未处理 {counts.unresolved_count} · 未查看 {counts.unread_count}</div>
        </div>
        <button className="v2-link" onClick={onBack}>返回</button>
      </div>

      <div className="v2-today-list" ref={listRef} onScroll={handleScroll} data-testid="today-list">
        {Object.entries(groups).map(([label, items]) => (
          <div key={label} className="v2-today-group">
            <div className="v2-today-group-title">{label}</div>
            {items.map((t) => (
              <div key={t.id} className={`v2-today-item ${t.unread ? 'unread' : ''}`} data-testid={`task-${t.id}`}>
                <button
                  className="v2-today-item-main"
                  onClick={() => onRead?.(t.id)}
                  aria-label={`${t.unread ? '新，' : ''}${t.customer_name}：${t.summary}`}
                >
                  <span className="v2-today-dot" aria-hidden="true">
                    {t.unread && <i className="v2-dot" />}
                  </span>
                  <span className="v2-today-main">
                    <strong>{t.customer_name}{t.unread && <em className="v2-new">新</em>}</strong>
                    <span>{t.summary}</span>
                    <small>{t.date}</small>
                  </span>
                </button>
                {!t.handled_at && (
                  <button className="v2-btn secondary v2-today-handle" onClick={() => onHandle?.(t.id)}>处理</button>
                )}
                {t.handled_at && <span className="v2-today-handled">已处理</span>}
              </div>
            ))}
          </div>
        ))}
        {tasks.length === 0 && <div className="v2-state">今日没有待处理事项</div>}
      </div>
    </div>
  )
}
