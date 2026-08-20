import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppHeader from '../../components/v1/AppHeader.jsx'
import BottomNavigation from '../../components/v1/BottomNavigation.jsx'
import { api } from '../../api.js'

const MVP_SCENARIOS = [
  '手动创建服务和客户套餐',
  '核销已有套餐并正确显示余额',
  '尝试核销不存在的套餐并得到提醒',
  '一句话拆分多项服务和商品',
  '新客户出现时先询问是否新增',
  '模糊客户查询展示最多 3 位候选',
  '“做脸”建议匹配“面部清洁”',
  '多张同类卡必须人工选择',
  '删除客户或记录后从回收站恢复',
  '修改提示词后生成新版本并可回退',
  '客户列表展示最后消费服务和日期，并按最后消费日期倒序',
  '从客户列表进入客户概览，再进入某项服务详情查看多张套餐卡',
  '多项操作统一确认时，一项失败则整组不写入',
  '删除并恢复一次套餐核销后，余额分别回退并恢复到正确值',
]

const ENTRIES = [
  { label: '对话记账（自然语言）', to: '/' },
  { label: '客户账本（三级详情）', to: '/customers' },
  { label: '服务管理与回收站', to: '/settings' },
  { label: '系统提示词管理', to: '/settings/prompt' },
]

export default function VerifyStage4() {
  const [health, setHealth] = useState(null)
  const [model, setModel] = useState(null)
  const [promptVersion, setPromptVersion] = useState(null)

  const load = useCallback(async () => {
    try { setHealth(await fetch('/api/health').then((r) => r.json())) } catch (e) { setHealth({ status: 'error' }) }
    try { setModel(await fetch('/api/config/model-status').then((r) => r.json())) } catch (e) { setModel({ configured: false }) }
    try { setPromptVersion((await api.getPrompt()).version) } catch (e) { /* 忽略 */ }
  }, [])

  useEffect(() => { load() }, [load])

  const backendOk = health?.status === 'ok'
  const dbOk = health?.database === 'ok'
  const modelOk = model?.configured === true

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>阶段4 · 本地验收</h2>
          <p className="v1-hint">发财·美容店智能客户账本 本地测试版 · 验收入口与系统状态。</p>
        </div>

        <div className="v1-panel">
          <h2>系统状态</h2>
          <div className="v1-row"><span className="k">前端页面</span><span className="v ok">已加载</span></div>
          <div className="v1-row"><span className="k">后端服务</span><span className={`v ${backendOk ? 'ok' : 'bad'}`}>{backendOk ? '正常' : '异常'}</span></div>
          <div className="v1-row"><span className="k">SQLite 数据库</span><span className={`v ${dbOk ? 'ok' : 'bad'}`}>{dbOk ? '连接正常' : '连接失败'}</span></div>
          <div className="v1-row"><span className="k">模型配置</span><span className={`v ${modelOk ? 'ok' : 'warn'}`}>{modelOk ? '已配置' : '未配置'}</span></div>
          {promptVersion != null && <div className="v1-row"><span className="k">提示词版本</span><span className="v">v{promptVersion}</span></div>}
        </div>

        <div className="v1-panel">
          <h2>功能入口</h2>
          <div style={{ display: 'grid', gap: 8 }}>
            {ENTRIES.map((e) => (
              <Link key={e.to} className="v1-test-btn" to={e.to}>{e.label} →</Link>
            ))}
          </div>
        </div>

        <div className="v1-panel">
          <h2>MVP 验收清单（14 项）</h2>
          {MVP_SCENARIOS.map((s, i) => (
            <div key={i} className="v1-row">
              <span className="k" style={{ fontSize: 13 }}>{i + 1}. {s}</span>
              <span className="v pending">☐</span>
            </div>
          ))}
        </div>

        <div className="v1-panel">
          <h2>已知限制与后续建议</h2>
          <ul className="v1-hint" style={{ paddingLeft: 18, lineHeight: 1.8, margin: 0 }}>
            <li>仅本机运行，不公开部署、无账号、无邀请码。</li>
            <li>仅使用化名测试数据，勿录入真实客户敏感信息。</li>
            <li>正式使用前请运行 ./backup.sh 备份数据库。</li>
            <li>后续（不在本次范围）：邀请码/身份认证、公开部署、到店提醒、库存、多店等。</li>
          </ul>
        </div>
      </div>
      <BottomNavigation />
    </div>
  )
}
