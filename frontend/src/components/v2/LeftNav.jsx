// 电脑 Web 左侧固定导航：对话 / 全部客户 / 管理与设置（不展示 AI 技术编辑入口）。
import { DRAWER_ITEMS } from './Drawer.jsx'

export default function LeftNav({ active, onNavigate }) {
  return (
    <aside className="v2-left-nav" data-testid="left-nav">
      <div className="v2-left-brand">
        <span className="v2-logo">发</span>
        <strong>发财</strong>
      </div>
      <nav aria-label="主导航">
        {DRAWER_ITEMS.map((item) => (
          <button
            key={item.key}
            className={`v2-left-item ${active === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
          >
            <i aria-hidden="true">{item.icon}</i>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}
