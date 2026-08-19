import { useCallback, useEffect, useState } from 'react'

function StatusRow({ label, value, tone }) {
  return (
    <div className="status-row">
      <span className="status-label">{label}</span>
      <span className={`status-value ${tone || ''}`}>{value}</span>
    </div>
  )
}

export default function VerifyStage0() {
  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState('')
  const [modelStatus, setModelStatus] = useState(null)
  const [checkResult, setCheckResult] = useState(null)
  const [checking, setChecking] = useState(false)

  const loadHealth = useCallback(async () => {
    setHealthError('')
    try {
      const res = await fetch('/api/health')
      const data = await res.json()
      setHealth(data)
    } catch (e) {
      setHealthError('无法连接后端：' + e.message)
      setHealth(null)
    }
  }, [])

  const loadModelStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/config/model-status')
      const data = await res.json()
      setModelStatus(data)
    } catch (e) {
      setModelStatus({ error: '无法读取模型配置状态' })
    }
  }, [])

  useEffect(() => {
    loadHealth()
    loadModelStatus()
  }, [loadHealth, loadModelStatus])

  const runCheck = async () => {
    setChecking(true)
    setCheckResult(null)
    try {
      const res = await fetch('/api/model/check', { method: 'POST' })
      const data = await res.json()
      setCheckResult(data)
    } catch (e) {
      setCheckResult({ success: false, message: '检查请求失败：' + e.message })
    } finally {
      setChecking(false)
    }
  }

  const backendOk = health && health.status === 'ok'
  const dbOk = health && health.database === 'ok'
  const configured = modelStatus?.configured === true

  return (
    <main className="page">
      <h1>阶段0 验证页</h1>
      <p className="subtitle">项目骨架与模型连通性检查（本页绝不显示 API Key）</p>

      <section className="card">
        <h2>前端状态</h2>
        <StatusRow label="前端页面" value="已加载" tone="ok" />
      </section>

      <section className="card">
        <h2>后端与数据库状态</h2>
        {healthError ? (
          <StatusRow label="后端服务" value={healthError} tone="bad" />
        ) : health ? (
          <>
            <StatusRow label="后端服务" value={backendOk ? '正常' : '异常'} tone={backendOk ? 'ok' : 'bad'} />
            <StatusRow label="SQLite 数据库" value={dbOk ? '连接正常' : '连接失败'} tone={dbOk ? 'ok' : 'bad'} />
            {!dbOk && health.database_message && (
              <div className="hint">{health.database_message}</div>
            )}
          </>
        ) : (
          <StatusRow label="后端服务" value="检测中…" tone="pending" />
        )}
      </section>

      <section className="card">
        <h2>模型配置与连通性</h2>
        <StatusRow
          label="API Key"
          value={modelStatus == null ? '检测中…' : configured ? '已配置' : '未配置'}
          tone={modelStatus == null ? 'pending' : configured ? 'ok' : 'warn'}
        />
        {modelStatus && modelStatus.model_id && (
          <StatusRow label="模型 ID" value={modelStatus.model_id} />
        )}
        {modelStatus && modelStatus.api_base_url && (
          <StatusRow label="接口地址" value={modelStatus.api_base_url} />
        )}
        <div className="actions">
          <button onClick={runCheck} disabled={checking || !configured}>
            {checking ? '检测中…' : '检测模型连通性'}
          </button>
        </div>
        {!configured && modelStatus != null && (
          <p className="hint">请先在 backend/.env 中填写 DEEPSEEK_API_KEY，然后刷新本页再点击检测。</p>
        )}
        {checkResult && (
          <StatusRow
            label="连通性"
            value={checkResult.success ? '连接成功' : '连接失败'}
            tone={checkResult.success ? 'ok' : 'bad'}
          />
        )}
        {checkResult && checkResult.message && (
          <div className="hint">{checkResult.message}</div>
        )}
      </section>

      <p className="footnote">本页面只展示“已配置/未配置”和连通状态，绝不显示 API Key 内容。</p>
    </main>
  )
}
