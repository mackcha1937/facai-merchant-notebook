import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

const MVP_SCENARIOS = [
  '手动创建服务和客户套餐（阶段1）',
  '核销已有套餐并正确显示余额（阶段3）',
  '尝试核销不存在的套餐并得到提醒（阶段3）',
  '一句话拆分多项服务和商品（阶段3）',
  '新客户出现时先询问是否新增（阶段3）',
  '模糊客户查询展示最多 3 位候选（阶段3）',
  '“做脸”建议匹配“面部清洁”（阶段2）',
  '多张同类卡必须人工选择（阶段3）',
  '删除客户或记录后从回收站恢复（阶段1）',
  '修改提示词后生成新版本并可回退（阶段2）',
]

const FEATURES = [
  { label: '客户账本（列表/搜索/详情）', url: '/verify/stage-1' },
  { label: '服务项目管理', url: '/verify/stage-1' },
  { label: '套餐与余额（后端计算）', url: '/verify/stage-1' },
  { label: '自然语言解析（仅解析）', url: '/verify/stage-2' },
  { label: '自然语言记账（确认写入）', url: '/verify/stage-3' },
  { label: '系统提示词管理', url: '/settings/prompt' },
  { label: '回收站恢复', url: '/verify/stage-1' },
]

export default function VerifyStage4() {
  const [health, setHealth] = useState(null)
  const [modelStatus, setModelStatus] = useState(null)
  const [prompt, setPrompt] = useState(null)

  const load = useCallback(async () => {
    try {
      const h = await fetch('/api/health').then((r) => r.json())
      setHealth(h)
    } catch (e) {
      setHealth({ status: 'error' })
    }
    try {
      setModelStatus(await fetch('/api/config/model-status').then((r) => r.json()))
    } catch (e) {
      setModelStatus({ configured: false })
    }
    try {
      setPrompt(await api.getPrompt())
    } catch (e) {
      /* 忽略 */
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const backendOk = health?.status === 'ok'
  const dbOk = health?.database === 'ok'
  const modelOk = modelStatus?.configured === true

  return (
    <main className="page">
      <h1>阶段4 验收总览</h1>
      <p className="subtitle">美容店智能客户账本 MVP · 本地测试版 · 验收入口与系统状态</p>

      <section className="card">
        <h2>系统状态</h2>
        <div className="status-row">
          <span className="status-label">前端页面</span>
          <span className="status-value ok">已加载</span>
        </div>
        <div className="status-row">
          <span className="status-label">后端服务</span>
          <span className={`status-value ${backendOk ? 'ok' : 'bad'}`}>{backendOk ? '正常' : '异常'}</span>
        </div>
        <div className="status-row">
          <span className="status-label">SQLite 数据库</span>
          <span className={`status-value ${dbOk ? 'ok' : 'bad'}`}>{dbOk ? '连接正常' : '连接失败'}</span>
        </div>
        <div className="status-row">
          <span className="status-label">模型配置</span>
          <span className={`status-value ${modelOk ? 'ok' : 'warn'}`}>{modelOk ? '已配置' : '未配置'}</span>
        </div>
        {prompt && (
          <div className="status-row">
            <span className="status-label">当前提示词版本</span>
            <span className="status-value">v{prompt.version}</span>
          </div>
        )}
      </section>

      <section className="card">
        <h2>功能入口</h2>
        <ul className="list">
          {FEATURES.map((f, i) => (
            <li key={i} className="list-item">
              <span>{f.label}</span>
              <a href={f.url}>打开 →</a>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>MVP 验收清单（PRD 第9节）</h2>
        <ul className="list">
          {MVP_SCENARIOS.map((s, i) => (
            <li key={i} className="list-item">
              <span>{i + 1}. {s}</span>
              <span className="muted">☐ 待验收</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>已知限制与后续建议</h2>
        <ul className="muted" style={{ paddingLeft: 18, lineHeight: 1.8 }}>
          <li>仅本机运行，不公开部署、无邀请码、无账号。</li>
          <li>仅使用化名测试数据，勿录入真实客户敏感信息。</li>
          <li>正式使用前需备份数据库：运行 ./backup.sh。</li>
          <li>后续（不在本次范围）：邀请码/身份认证、公开部署、到店提醒、库存、多店等。</li>
        </ul>
      </section>
    </main>
  )
}
