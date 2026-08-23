import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'

export default function VerifyV2Stage7() {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.getStage7Status().then(setStatus).catch((e) => setError(e.message)) }, [])
  return <main className="page" style={{ maxWidth: 900 }}><section className="card">
    <h1>发财 V2 · 阶段7（离线测评与发布治理）</h1><p>60条JSONL用例先登记，未执行项保持阻塞；人工结果完整导入且安全门槛100%后，管理员才能二次确认发布或回滚。</p>
    <p><Link to="/admin/evaluations">打开管理员测评台</Link> · <Link to="/verify/v2-stage-6">阶段6回归</Link> · <Link to="/verify/v2-stage-8">阶段8总验收</Link></p>
  </section>{error && <div className="error-banner">{error}</div>}
  <section className="card"><h2>能力边界</h2>{status && Object.entries(status.capabilities).map(([key, value]) => <div className="list-item" key={key}><span>{key}</span><strong>{value ? '已具备' : '未建设'}</strong></div>)}
    <div className="list-item"><span>真实模型 / 外部服务</span><strong>0 / 0</strong></div><div className="list-item"><span>公开部署</span><strong>未开始</strong></div>
  </section></main>
}
