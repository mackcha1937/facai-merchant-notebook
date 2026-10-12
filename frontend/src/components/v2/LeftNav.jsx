// 电脑 Web 左侧固定导航：对话 / 全部客户 / 管理与设置（不展示 AI 技术编辑入口）。
import { DRAWER_ITEMS } from './Drawer.jsx'
import Icon from './Icons.jsx'

export default function LeftNav({ active, onNavigate, onLogout }) {
  return (
    <aside className="v2-left-nav" data-testid="left-nav">
      <a className="v2-left-brand" href="/" aria-label="发财产品首页">
        <span className="v2-logo">发</span>
        <strong>发财</strong>
      </a>
      <nav aria-label="主导航">
        {DRAWER_ITEMS.map((item) => (
          <button
            key={item.key}
            className={`v2-left-item ${active === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
          >
            <i aria-hidden="true"><Icon name={item.icon} size={22} /></i>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <a className="v2-left-home" href="/">
        <i aria-hidden="true"><Icon name="home" size={20} /></i>
        <span>返回产品首页</span>
      </a>
      <button className="v2-left-logout" type="button" onClick={onLogout}>退出登录</button>
    </aside>
  )
}
