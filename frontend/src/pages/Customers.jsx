import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [q, setQ] = useState('')
  const [newName, setNewName] = useState('')
  const [newAliases, setNewAliases] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setCustomers(await api.getCustomers(q))
    } catch (e) {
      setError(e.message)
    }
  }, [q])

  useEffect(() => {
    load()
  }, [load])

  const createCustomer = async (e) => {
    e.preventDefault()
    try {
      await api.createCustomer({
        display_name: newName.trim(),
        aliases: newAliases.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
      })
      setNewName('')
      setNewAliases('')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="page">
      <h1>客户账本</h1>

      {error && <div className="error-banner">{error}</div>}

      <div className="search-bar">
        <input placeholder="搜索化名或别名，如：小红 / 红姐" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <form className="inline-form" onSubmit={createCustomer}>
        <input placeholder="客户化名（必填）" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <input placeholder="别名，逗号分隔（可选）" value={newAliases} onChange={(e) => setNewAliases(e.target.value)} />
        <button type="submit">新增客户</button>
      </form>

      <ul className="list">
        {customers.map((c) => (
          <li key={c.id} className="list-item">
            <div className="list-item-main">
              <strong>{c.display_name}</strong>
              <span className="muted">{c.aliases.map((a) => a.alias).join('、') || '（无别名）'}</span>
            </div>
            <Link className="btn-link" to={`/customers/${c.id}`}>查看 →</Link>
          </li>
        ))}
        {customers.length === 0 && <li className="muted empty">暂无客户。</li>}
      </ul>
    </main>
  )
}
