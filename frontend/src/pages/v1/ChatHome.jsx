import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'

export default function ChatHome() {
  return (
    <div className="v1-app">
      <AppHeader />
      <div className="v1-content v1-chat">
        <div className="v1-day">2026年8月20日</div>
        <div className="v1-message v1-assistant">
          下午好～直接告诉我客户今天买了什么、做了什么，写入前我会请你确认。
        </div>
        <div className="v1-message v1-user">小蓝今天肩颈按摩1次</div>
      </div>
      <div className="v1-composer">
        <input placeholder="继续输入购买、核销或查询" disabled />
        <button className="v1-send" disabled>➜</button>
      </div>
      <BottomNavigation />
    </div>
  )
}
