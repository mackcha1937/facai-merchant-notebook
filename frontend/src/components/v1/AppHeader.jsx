export default function AppHeader({ onSearch, onAdd }) {
  return (
    <header className="v1-header">
      <div className="v1-brand">
        <div className="v1-logo">发</div>
        <div>
          <strong>发财</strong>
          <small>智能客户账本</small>
        </div>
      </div>
      <div className="v1-header-actions">
        <button className="v1-icon-btn" onClick={onSearch} aria-label="搜索">⌕</button>
        <button className="v1-icon-btn" onClick={onAdd} aria-label="新增">＋</button>
      </div>
    </header>
  )
}
