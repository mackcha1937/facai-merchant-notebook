import { useCallback, useEffect, useState } from 'react'
import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'
import { ErrorState } from '../../components/v1/StateComponents.jsx'

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
      setHealth(await res.json())
    } catch (e) {
      setHealthError('无法连接后端：' + e.message)
      setHealth(null)
    }
  }, [])

  const loadModelStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/config/model-status')
      setModelStatus(await res.json())
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
      setCheckResult(await res.json())
    } catch (e) {
      setCheckResult({ success: false, message: '检查请求失败：' + e.message })
    } finally {
      setChecking(false)
    }
  }

  const backendOk = health?.status === 'ok'
  const dbOk = health?.database === 'ok'
  const configured = modelStatus?.configured === true

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ paddingBottom: 20 }}>
        <div className="v1-panel">
          <h2>阶段0 · 前端骨架</h2>
          <div className="v1-row"><span className="k">设计系统（Token）</span><span className="v ok">已加载</span></div>
          <div className="v1-row"><span className="k">AppHeader</span><span className="v ok">已渲染</span></div>
          <div className="v1-row"><span className="k">BottomNavigation</span><span className="v ok">已渲染</span></div>
          <div className="v1-row"><span className="k">主色</span><span className="v" style={{ color: 'var(--c-primary)' }}>#5D75DB</span></div>
        </div>

        <div className="v1-panel">
          <h2>后端与数据库</h2>
          {healthError ? (
            <ErrorState text={healthError} />
          ) : health ? (
            <>
              <div className="v1-row"><span className="k">后端服务</span><span className={`v ${backendOk ? 'ok' : 'bad'}`}>{backendOk ? '正常' : '异常'}</span></div>
              <div className="v1-row"><span className="k">SQLite 数据库</span><span className={`v ${dbOk ? 'ok' : 'bad'}`}>{dbOk ? '连接正常' : '连接失败'}</span></div>
            </>
          ) : (
            <div className="v1-row"><span className="k">后端服务</span><span className="v pending">检测中…</span></div>
          )}
        </div>

        <div className="v1-panel">
          <h2>模型配置与连通性</h2>
          <div className="v1-row">
            <span className="k">API Key</span>
            <span className={`v ${modelStatus == null ? 'pending' : configured ? 'ok' : 'warn'}`}>
              {modelStatus == null ? '检测中…' : configured ? '已配置' : '未配置'}
            </span>
          </div>
          {modelStatus?.model_id && (
            <div className="v1-row"><span className="k">模型 ID</span><span className="v">{modelStatus.model_id}</span></div>
          )}
          <div style={{ marginTop: 12 }}>
            <button className="v1-btn" onClick={runCheck} disabled={checking || !configured}>
              {checking ? '检测中…' : '检测模型连通性'}
            </button>
          </div>
          {!configured && modelStatus != null && (
            <p style={{ color: 'var(--c-text-weak)', fontSize: 13 }}>
              请先在 backend/.env 中填写 DEEPSEEK_API_KEY，再点击检测。
            </p>
          )}
          {checkResult && (
            <div className="v1-row" style={{ marginTop: 8 }}>
              <span className="k">连通性</span>
              <span className={`v ${checkResult.success ? 'ok' : 'bad'}`}>{checkResult.success ? '连接成功' : '连接失败'}</span>
            </div>
          )}
          {checkResult?.message && (
            <p style={{ color: 'var(--c-text-weak)', fontSize: 13, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {checkResult.message}
            </p>
          )}
        </div>

        <p style={{ padding: '0 16px', color: 'var(--c-text-weak)', fontSize: 12 }}>
          本页只展示“已配置/未配置”和连通状态，绝不显示 API Key。
        </p>
      </div>
      <BottomNavigation />
    </div>
  )
}
