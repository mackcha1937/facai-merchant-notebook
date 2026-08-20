import { Link } from 'react-router-dom'
import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'

const CHECKS = [
  '客户列表：展示最后消费服务与日期，按最后消费倒序',
  '客户二级详情：列表 → 客户概览（按服务类型）→ 服务详情（多卡）',
  '新增客户、创建套餐、删除恢复',
  '服务管理：新增/停用/删除',
  '套餐余额 = 总次数 − (历史已用 + 未删除核销记录)',
  '删除/恢复核销记录后余额自动回退/恢复',
]

export default function VerifyStage1() {
  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>阶段1 · 基础账本与分层查看</h2>
          <p style={{ color: 'var(--c-text-secondary)', fontSize: 14 }}>
            本阶段完成客户账本 Sheet（三级详情）、服务管理、回收站，以及权威余额计算。
          </p>
          <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
            <Link className="v1-btn" to="/customers" style={{ textAlign: 'center', textDecoration: 'none', lineHeight: '44px' }}>
              打开客户账本 Sheet
            </Link>
            <Link className="v1-btn secondary" to="/settings" style={{ textAlign: 'center', textDecoration: 'none', lineHeight: '44px' }}>
              打开服务管理与回收站
            </Link>
          </div>
        </div>

        <div className="v1-panel">
          <h2>验收清单</h2>
          {CHECKS.map((c, i) => (
            <div key={i} className="v1-row">
              <span className="k" style={{ fontSize: 13 }}>{i + 1}. {c}</span>
              <span className="v pending">待验收</span>
            </div>
          ))}
        </div>
      </div>
      <BottomNavigation />
    </div>
  )
}
