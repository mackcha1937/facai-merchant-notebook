import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: '首页', end: true },
  { to: '/customers', label: '客户' },
  { to: '/record', label: '记账' },
  { to: '/services', label: '服务' },
  { to: '/trash', label: '回收站' },
  { to: '/settings/prompt', label: '设置' },
]

export default function AppLayout() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">美容店账本</div>
        <nav className="app-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'app-nav-item active' : 'app-nav-item')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <div className="app-main">
        <Outlet />
      </div>
    </div>
  )
}
