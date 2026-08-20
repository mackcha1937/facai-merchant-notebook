import { Link } from 'react-router-dom'
import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'

const CHECKS = [
  '对话中输入自然语言 → 聊天内确认卡',
  '确认卡可修改次数、日期，多卡时可选择具体卡',
  '修改后重新预检查，显示确认后余额',
  '确认入账后转只读成功态，显示入账日期与最新余额',
  '新客户确认创建后再继续原操作',
  '多项操作统一确认：一项失败整组不写入',
  '重复确认同一建议不会重复入账',
]

export default function VerifyStage3() {
  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>阶段3 · 确认写入与同步</h2>
          <p className="v1-hint">完整闭环：输入 → 解析 → 修改 → 确认 → 写入 → 结果反馈 → 客户核对。</p>
          <div style={{ marginTop: 12 }}>
            <Link className="v1-btn" to="/" style={{ display: 'block', textAlign: 'center', textDecoration: 'none', lineHeight: '44px' }}>
              打开对话首页（输入记账）
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
