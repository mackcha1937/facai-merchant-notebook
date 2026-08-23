import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'

const label = (value) => value ? '通过/具备' : '未完成'

export default function VerifyV2Stage8() {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.getStage8Status().then(setStatus).catch((failure) => setError(failure.message)) }, [])
  return <main className="page" style={{ maxWidth: 920 }}>
    <section className="card"><h1>发财 V2 · 阶段8本地总验收</h1>
      <p>汇总阶段1～7回归、多日/多设备、失败降级、备份恢复、双端响应式、可访问性和安全基线。此页不代表已公开部署。</p>
      <nav className="stage8-nav" aria-label="验收页快速入口">
        <Link to="/app/chat">店主端</Link>
        <Link to="/admin/evaluations">管理员端</Link>
        <Link to="/verify/v2-stage-7">阶段7</Link>
      </nav>
    </section>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {!status && !error && <section className="card" aria-busy="true">正在读取本地验收结果…</section>}
    {status && <>
      <section className="card"><h2>完整联调能力</h2>
        {Object.entries(status.capabilities).map(([key, value]) => <div className="list-item" key={key}><span>{key}</span><strong>{label(value)}</strong></div>)}
      </section>
      <section className="card"><h2>数据库完整性</h2>
        <div className="list-item"><span>Migration</span><strong>{status.database.migration}</strong></div>
        <div className="list-item"><span>integrity_check</span><strong>{status.database.integrity}</strong></div>
        <div className="list-item"><span>外键错误</span><strong>{status.database.foreign_key_errors ?? '未知'}</strong></div>
      </section>
      <section className="card"><h2>明确边界</h2>
        <div className="list-item"><span>真实模型有效</span><strong>{status.runtime_boundaries.real_model_effective ? '已启用' : '关闭'}</strong></div>
        <div className="list-item"><span>外部Embedding / 外部发送</span><strong>{status.runtime_boundaries.external_embedding || status.runtime_boundaries.external_message_send ? '存在' : '0 / 0'}</strong></div>
        <div className="list-item"><span>生产认证</span><strong>{status.runtime_boundaries.production_authentication ? '已完成' : '未建设'}</strong></div>
        <div className="list-item"><span>公开部署</span><strong>{status.runtime_boundaries.public_deployment ? '已部署' : '未开始'}</strong></div>
      </section>
    </>}
  </main>
}
