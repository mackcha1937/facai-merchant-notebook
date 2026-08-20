import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

const TRASH_TYPE_LABEL = { customer: '客户', service: '服务项目', package: '套餐', ledger: '记录' }

export default function Trash() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try { setItems((await api.getTrash()).items) } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { load() }, [load])

  const restore = async (item) => {
    if (!window.confirm(`确定恢复“${item.name}”吗？`)) return
    try {
      if (item.type === 'customer') await api.restoreCustomer(item.id)
      else if (item.type === 'service') await api.restoreService(item.id)
      else if (item.type === 'package') await api.restorePackage(item.id)
      else if (item.type === 'ledger') await api.restoreLedger(item.id)
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <main className="page">
      <h1>回收站</h1>

      {error && <div className="error-banner">{error}</div>}

      <ul className="list">
        {items.map((item) => (
          <li key={`${item.type}-${item.id}`} className="list-item">
            <div className="list-item-main">
              <span className={`tag tag-${item.type}`}>{TRASH_TYPE_LABEL[item.type] || item.type}</span>
              <strong>{item.name}</strong>
              <span className="muted">{item.deleted_at ? String(item.deleted_at).slice(0, 19) : ''}</span>
            </div>
            <button onClick={() => restore(item)}>恢复</button>
          </li>
        ))}
        {items.length === 0 && <li className="muted empty">回收站为空。</li>}
      </ul>
      <p className="footnote">测试版只支持恢复，不提供永久删除。</p>
    </main>
  )
}
