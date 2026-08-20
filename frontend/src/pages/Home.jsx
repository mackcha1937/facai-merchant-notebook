import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function Home() {
  const [customers, setCustomers] = useState(0)
  const [services, setServices] = useState(0)

  useEffect(() => {
    api.getCustomers().then((c) => setCustomers(c.length)).catch(() => {})
    api.getServices().then((s) => setServices(s.length)).catch(() => {})
  }, [])

  return (
    <main className="page">
      <h1>首页</h1>
      <p className="subtitle">美容店智能客户账本 · 本地预览版（非最终版）</p>

      <section className="card stats">
        <div className="stat">
          <div className="stat-num">{customers}</div>
          <div className="stat-label">客户</div>
        </div>
        <div className="stat">
          <div className="stat-num">{services}</div>
          <div className="stat-label">服务项目</div>
        </div>
      </section>

      <section className="card">
        <h2>快捷入口</h2>
        <div className="quick-grid">
          <Link className="quick" to="/record">✍️ 记账（自然语言）</Link>
          <Link className="quick" to="/customers">👥 客户账本</Link>
          <Link className="quick" to="/services">🧴 服务项目</Link>
          <Link className="quick" to="/trash">🗑️ 回收站</Link>
          <Link className="quick" to="/settings/prompt">⚙️ 提示词设置</Link>
        </div>
      </section>

      <p className="footnote">这是可用的前端预览版，先看看效果；正式版后续再打磨。</p>
    </main>
  )
}
