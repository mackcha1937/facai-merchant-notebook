import { NavLink } from 'react-router-dom'

const ITEMS = [
  { to: '/', label: '对话', icon: '◉', end: true },
  { to: '/customers', label: '客户', icon: '♡', end: false },
  { to: '/settings', label: '设置', icon: '⚙', end: false },
]

export default function BottomNavigation() {
  return (
    <nav className="v1-nav">
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => (isActive ? 'v1-nav-item active' : 'v1-nav-item')}
        >
          <i>{item.icon}</i>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
