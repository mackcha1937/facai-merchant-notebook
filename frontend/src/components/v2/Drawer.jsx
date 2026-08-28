// 左侧抽屉：一级只允许 对话 / 全部客户 / 管理与设置 三个入口。
// 支持菜单按钮、遮罩、左滑、系统返回键关闭（关闭逻辑由 AppShell 的 back 处理）。
import Icon from './Icons.jsx'

export const DRAWER_ITEMS = [
  { key: 'chat', label: '对话', icon: 'chat' },
  { key: 'customer_index', label: '全部客户', icon: 'customers' },
  { key: 'management', label: '管理与设置', icon: 'settings' },
]

export default function Drawer({ open, onClose, onNavigate, active }) {
  if (!open) return null
  return (
    <div className="v2-drawer" data-testid="drawer">
      <div className="v2-drawer-backdrop" onClick={onClose} data-testid="drawer-backdrop" />
      <nav className="v2-drawer-panel" aria-label="主菜单" data-testid="drawer-panel">
        <a className="v2-drawer-head" href="/" aria-label="发财产品首页">
          <span className="v2-logo">发</span>
          <strong>发财</strong>
        </a>
        {DRAWER_ITEMS.map((item) => (
          <button
            key={item.key}
            className={`v2-drawer-item ${active === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
          >
            <i aria-hidden="true"><Icon name={item.icon} size={22} /></i>
            <span>{item.label}</span>
          </button>
        ))}
        <a className="v2-drawer-home" href="/">
          <i aria-hidden="true"><Icon name="home" size={20} /></i>
          <span>返回产品首页</span>
        </a>
      </nav>
    </div>
  )
}
