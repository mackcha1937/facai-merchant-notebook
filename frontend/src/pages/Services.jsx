import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Services() {
  const [services, setServices] = useState([])
  const [newName, setNewName] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try { setServices(await api.getServices()) } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { load() }, [load])

  const createService = async (e) => {
    e.preventDefault()
    try {
      await api.createService({ name: newName.trim() })
      setNewName('')
      await load()
    } catch (err) { setError(err.message) }
  }

  const toggleStatus = async (s) => {
    try {
      await api.updateService(s.id, { status: s.status === 'active' ? 'inactive' : 'active' })
      await load()
    } catch (err) { setError(err.message) }
  }

  const removeService = async (s) => {
    if (!window.confirm(`确定删除服务“${s.name}”吗？删除后进入回收站。`)) return
    try {
      await api.deleteService(s.id)
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <main className="page">
      <h1>服务项目</h1>

      {error && <div className="error-banner">{error}</div>}

      <form className="inline-form" onSubmit={createService}>
        <input placeholder="服务名称，如：面部清洁" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="submit">新增服务</button>
      </form>

      <ul className="list">
        {services.map((s) => (
          <li key={s.id} className="list-item">
            <div className="list-item-main">
              <strong>{s.name}</strong>
              <span className={`tag ${s.status === 'active' ? 'tag-active' : 'tag-inactive'}`}>{s.status === 'active' ? '启用中' : '已停用'}</span>
            </div>
            <div className="row-actions">
              <button onClick={() => toggleStatus(s)}>{s.status === 'active' ? '停用' : '启用'}</button>
              <button className="danger" onClick={() => removeService(s)}>删除</button>
            </div>
          </li>
        ))}
        {services.length === 0 && <li className="muted empty">暂无服务项目。</li>}
      </ul>
      <p className="footnote">停用的服务不能再用于新套餐，历史记录仍保留。</p>
    </main>
  )
}
