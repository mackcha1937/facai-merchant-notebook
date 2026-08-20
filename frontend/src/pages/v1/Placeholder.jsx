import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'

export default function Placeholder({ title = '待实现' }) {
  return (
    <div className="v1-app">
      <AppHeader />
      <div className="v1-content">
        <div className="v1-state">
          <span className="v1-state-icon">🚧</span>
          <span>{title}</span>
          <span style={{ color: 'var(--c-text-weak)', fontSize: 13 }}>
            将在后续阶段实现
          </span>
        </div>
      </div>
      <BottomNavigation />
    </div>
  )
}
