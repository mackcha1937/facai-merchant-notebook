import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'

const TRASH_LABEL = { customer: '客户', service: '服务项目', package: '套餐', ledger: '记录' }

export default function Settings() {
  const [tab, setTab] = useState('services')

  return (
    <div className="v1-app">
      <div className="v1-sheet">
        <div className="v1-sheet-handle" />
        <div className="v1-sheet-body">
          <div className="v1-sheet-title">
            <h2>设置</h2>
            <Link to="/" className="v1-btn secondary">关闭</Link>
          </div>

          <div className="v1-tabs">
            <button className={tab === 'services' ? 'v1-tab active' : 'v1-tab'} onClick={() => setTab('services')}>服务管理</button>
            <button className={tab === 'trash' ? 'v1-tab active' : 'v1-tab'} onClick={() => setTab('trash')}>回收站</button>
            <Link to="/settings/prompt" className={tab === 'prompt' ? 'v1-tab active' : 'v1-tab'}>提示词</Link>
          </div>

          {tab === 'services' && <ServicesManager />}
          {tab === 'trash' && <TrashList />}
        </div>
      </div>
    </div>
  )
}

function ServicesManager() {
  const [services, setServices] = useState([])
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try { setServices(await api.getServices()) } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { load() }, [load])

  const add = async (e) => {
    e.preventDefault()
    try {
      await api.createService({ name: name.trim() })
      setName('')
      await load()
    } catch (err) { setError(err.message) }
  }

  const toggle = async (s) => {
    try {
      await api.updateService(s.id, { status: s.status === 'active' ? 'inactive' : 'active' })
      await load()
    } catch (err) { setError(err.message) }
  }

  const remove = async (s) => {
    if (!window.confirm(`确定删除服务「${s.name}」吗？删除后进入回收站。`)) return
    try { await api.deleteService(s.id); await load() } catch (err) { setError(err.message) }
  }

  return (
    <>
      {error && <div className="v1-error-banner">{error}</div>}
      <form className="v1-inline-form" onSubmit={add}>
        <input placeholder="服务名称，如：面部清洁" value={name} onChange={(e) => setName(e.target.value)} />
        <button className="v1-btn" type="submit">新增</button>
      </form>
      <div className="v1-customer-list">
        {services.map((s) => (
          <div key={s.id} className="v1-customer-item" style={{ cursor: 'default' }}>
            <span className="v1-service-icon">{s.name.slice(0, 1)}</span>
            <span className="v1-customer-main">
              <span className="v1-customer-name">{s.name}</span>
              <span className="v1-customer-note">{s.status === 'active' ? '启用中' : '已停用'}</span>
            </span>
            <span className="v1-row-actions">
              <button className="v1-btn secondary" onClick={() => toggle(s)}>{s.status === 'active' ? '停用' : '启用'}</button>
              <button className="v1-btn danger" onClick={() => remove(s)}>删除</button>
            </span>
          </div>
        ))}
        {services.length === 0 && <div className="v1-state"><span>暂无服务项目</span></div>}
      </div>
    </>
  )
}

function TrashList() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try { setItems((await api.getTrash()).items) } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { load() }, [load])

  const restore = async (item) => {
    if (!window.confirm(`确定恢复「${item.name}」吗？`)) return
    try {
      if (item.type === 'customer') await api.restoreCustomer(item.id)
      else if (item.type === 'service') await api.restoreService(item.id)
      else if (item.type === 'package') await api.restorePackage(item.id)
      else if (item.type === 'ledger') await api.restoreLedger(item.id)
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <>
      {error && <div className="v1-error-banner">{error}</div>}
      <div className="v1-customer-list">
        {items.map((item) => (
          <div key={`${item.type}-${item.id}`} className="v1-customer-item" style={{ cursor: 'default' }}>
            <span className="v1-service-icon">{TRASH_LABEL[item.type]?.slice(0, 1)}</span>
            <span className="v1-customer-main">
              <span className="v1-customer-name">{TRASH_LABEL[item.type] || item.type} · {item.name}</span>
              <span className="v1-customer-note">删除于 {String(item.deleted_at || '').slice(0, 19)}</span>
            </span>
            <button className="v1-btn secondary" onClick={() => restore(item)}>恢复</button>
          </div>
        ))}
        {items.length === 0 && <div className="v1-state"><span>回收站为空</span></div>}
      </div>
    </>
  )
}
