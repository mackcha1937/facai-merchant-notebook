// 左侧抽屉：一级只允许 对话 / 全部客户 / 管理与设置 三个入口。
// 支持菜单按钮、遮罩、左滑、系统返回键关闭（关闭逻辑由 AppShell 的 back 处理）。
export const DRAWER_ITEMS = [
  { key: 'chat', label: '对话', icon: '◉' },
  { key: 'customer_index', label: '全部客户', icon: '♡' },
  { key: 'management', label: '管理与设置', icon: '⚙' },
]

export default function Drawer({ open, onClose, onNavigate, active }) {
  if (!open) return null
  return (
    <div className="v2-drawer" data-testid="drawer">
      <div className="v2-drawer-backdrop" onClick={onClose} data-testid="drawer-backdrop" />
      <nav className="v2-drawer-panel" aria-label="主菜单" data-testid="drawer-panel">
        <div className="v2-drawer-head">
          <span className="v2-logo">发</span>
          <strong>发财</strong>
        </div>
        {DRAWER_ITEMS.map((item) => (
          <button
            key={item.key}
            className={`v2-drawer-item ${active === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
          >
            <i aria-hidden="true">{item.icon}</i>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
