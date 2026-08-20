export function EmptyState({ icon = '☐', text = '暂无内容' }) {
  return (
    <div className="v1-state">
      <span className="v1-state-icon">{icon}</span>
      <span>{text}</span>
    </div>
  )
}

export function ErrorState({ text = '出错了' }) {
  return (
    <div className="v1-state v1-error">
      <span className="v1-state-icon">⚠</span>
      <span>{text}</span>
    </div>
  )
}

export function LoadingIndicator({ text = '加载中…' }) {
  return (
    <div className="v1-state">
      <span className="v1-spinner" />
      <span>{text}</span>
    </div>
  )
}
