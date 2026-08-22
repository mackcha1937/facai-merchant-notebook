// 手机顶部：☰ 发财 今日事项 N 🔴（固定，所有工作区可见）。
export default function TopBar({ onMenu, onToday, unresolvedCount = 0, unreadCount = 0 }) {
  return (
    <header className="v2-topbar" data-testid="topbar">
      <button className="v2-menu-btn" onClick={onMenu} aria-label="菜单">☰</button>
      <div className="v2-brand">
        <span className="v2-logo">发</span>
        <strong>发财</strong>
      </div>
      <button
        className="v2-today-btn"
        onClick={onToday}
        aria-label={`今日事项，${unresolvedCount} 条未处理${unreadCount > 0 ? '，有未查看新事项' : ''}`}
      >
        今日事项 {unresolvedCount}
        {unreadCount > 0 && <span className="v2-dot" aria-hidden="true" />}
        {unreadCount > 0 && <span className="v2-new">新</span>}
      </button>
    </header>
  )
}
