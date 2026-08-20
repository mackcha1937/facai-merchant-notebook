import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, yuanToCents, formatPrice } from '../api.js'

const PACKAGE_STATUS_LABEL = { active: '有效', exhausted: '已用完', inactive: '停用' }
const ENTRY_TYPE_LABEL = {
  package_purchase: '套餐购买',
  package_consumption: '套餐核销',
  one_time_service: '一次性服务',
  product_purchase: '商品购买',
}

export default function CustomerDetail() {
  const { id } = useParams()
  const customerId = Number(id)
  const [detail, setDetail] = useState(null)
  const [services, setServices] = useState([])
  const [error, setError] = useState('')

  const [pkgService, setPkgService] = useState('')
  const [pkgTotal, setPkgTotal] = useState('')
  const [pkgPrice, setPkgPrice] = useState('')
  const [pkgDate, setPkgDate] = useState('')

  const [editingPkg, setEditingPkg] = useState(null)
  const [editTotal, setEditTotal] = useState('')
  const [editUsed, setEditUsed] = useState('')
  const [editPrice, setEditPrice] = useState('')

  const [entryType, setEntryType] = useState('one_time_service')
  const [entryService, setEntryService] = useState('')
  const [entryProduct, setEntryProduct] = useState('')
  const [entryQty, setEntryQty] = useState('1')
  const [entryPrice, setEntryPrice] = useState('')

  const load = useCallback(async () => {
    try {
      const [d, s] = await Promise.all([api.getCustomer(customerId), api.getServices()])
      setDetail(d)
      setServices(s)
    } catch (e) {
      setError(e.message)
    }
  }, [customerId])

  useEffect(() => {
    load()
  }, [load])

  if (!detail) {
    return (
      <main className="page">
        <Link to="/customers">← 返回客户列表</Link>
        {error && <div className="error-banner">{error}</div>}
        <p className="muted">加载中…</p>
      </main>
    )
  }

  const activeServices = services.filter((s) => s.status === 'active')

  const createPackage = async (e) => {
    e.preventDefault()
    if (!pkgService || !pkgTotal) {
      setError('请选择服务并填写总次数')
      return
    }
    try {
      await api.createPackage(customerId, {
        service_id: Number(pkgService),
        total_count: Number(pkgTotal),
        price_cents: yuanToCents(pkgPrice),
        purchased_on: pkgDate || null,
      })
      setPkgService('')
      setPkgTotal('')
      setPkgPrice('')
      setPkgDate('')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const startEdit = (p) => {
    setEditingPkg(p.id)
    setEditTotal(String(p.total_count))
    setEditUsed(String(p.used_count))
    setEditPrice(p.price_cents == null ? '' : String(p.price_cents / 100))
  }

  const saveEdit = async (p) => {
    try {
      await api.updatePackage(p.id, {
        total_count: Number(editTotal),
        used_count: Number(editUsed),
        price_cents: yuanToCents(editPrice),
      })
      setEditingPkg(null)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const removePackage = async (p) => {
    if (!window.confirm('确定删除这张套餐卡吗？删除后进入回收站。')) return
    try {
      await api.deletePackage(p.id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const createEntry = async (e) => {
    e.preventDefault()
    const payload = { entry_type: entryType, quantity: Number(entryQty) || 1, price_cents: yuanToCents(entryPrice) }
    if (entryType === 'one_time_service') payload.service_id = Number(entryService)
    else payload.product_name = entryProduct.trim()
    try {
      await api.createLedger(customerId, payload)
      setEntryProduct('')
      setEntryPrice('')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const removeEntry = async (e) => {
    if (!window.confirm('确定删除这条记录吗？删除后进入回收站。')) return
    try {
      await api.deleteLedger(e.id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="page">
      <div className="detail-header">
        <Link to="/customers">← 返回客户列表</Link>
        <h1 style={{ margin: 0, fontSize: 18 }}>{detail.display_name}</h1>
        <span className="muted">别名：{detail.aliases.map((a) => a.alias).join('、') || '（无）'}</span>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="card">
        <h2>套餐卡（剩余 = 总次数 − 已用）</h2>
        <ul className="list">
          {detail.packages.map((p) => (
            <li key={p.id} className="list-item column">
              {editingPkg === p.id ? (
                <div className="edit-grid">
                  <label>服务：{p.service_name}</label>
                  <label>总次数 <input value={editTotal} onChange={(e) => setEditTotal(e.target.value)} /></label>
                  <label>已用次数 <input value={editUsed} onChange={(e) => setEditUsed(e.target.value)} /></label>
                  <label>价格（元）<input value={editPrice} onChange={(e) => setEditPrice(e.target.value)} /></label>
                  <div className="row-actions">
                    <button onClick={() => saveEdit(p)}>保存</button>
                    <button className="link" onClick={() => setEditingPkg(null)}>取消</button>
                  </div>
                </div>
              ) : (
                <>
                  <div>
                    <strong>{p.service_name}</strong>
                    <span className={`tag tag-${p.status}`}>{PACKAGE_STATUS_LABEL[p.status] || p.status}</span>
                  </div>
                  <div className="muted">
                    总 {p.total_count} 次 · 已用 {p.used_count} 次 · 剩余 {p.remaining_count} 次
                    {p.price_cents != null && ` · ${formatPrice(p.price_cents)} 元`}
                    {p.purchased_on && ` · 购买 ${p.purchased_on}`}
                  </div>
                  <div className="row-actions">
                    <button onClick={() => startEdit(p)}>编辑</button>
                    <button className="danger" onClick={() => removePackage(p)}>删除</button>
                  </div>
                </>
              )}
            </li>
          ))}
          {detail.packages.length === 0 && <li className="muted empty">暂无套餐卡。</li>}
        </ul>

        <form className="inline-form" onSubmit={createPackage}>
          <select value={pkgService} onChange={(e) => setPkgService(e.target.value)}>
            <option value="">选择服务…</option>
            {activeServices.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input placeholder="总次数" type="number" min="1" value={pkgTotal} onChange={(e) => setPkgTotal(e.target.value)} />
          <input placeholder="价格（元，可选）" value={pkgPrice} onChange={(e) => setPkgPrice(e.target.value)} />
          <input placeholder="购买日期（可选）" value={pkgDate} onChange={(e) => setPkgDate(e.target.value)} />
          <button type="submit">新增套餐</button>
        </form>
      </section>

      <section className="card">
        <h2>消费记录</h2>
        <ul className="list">
          {detail.ledger.map((e) => (
            <li key={e.id} className="list-item">
              <div>
                <strong>{ENTRY_TYPE_LABEL[e.entry_type] || e.entry_type}</strong>
                <span className="muted">
                  {' '}{e.entry_type === 'product_purchase' ? e.product_name : e.service_name} × {e.quantity}
                  {e.price_cents != null && ` · ${formatPrice(e.price_cents)} 元`}
                </span>
              </div>
              <button className="danger" onClick={() => removeEntry(e)}>删除</button>
            </li>
          ))}
          {detail.ledger.length === 0 && <li className="muted empty">暂无记录。</li>}
        </ul>

        <form className="inline-form" onSubmit={createEntry}>
          <select value={entryType} onChange={(e) => setEntryType(e.target.value)}>
            <option value="one_time_service">一次性服务</option>
            <option value="product_purchase">商品购买</option>
          </select>
          {entryType === 'one_time_service' ? (
            <select value={entryService} onChange={(e) => setEntryService(e.target.value)}>
              <option value="">选择服务…</option>
              {services.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          ) : (
            <input placeholder="商品名称" value={entryProduct} onChange={(e) => setEntryProduct(e.target.value)} />
          )}
          <input placeholder="数量" type="number" min="1" value={entryQty} onChange={(e) => setEntryQty(e.target.value)} />
          <input placeholder="价格（元，可选）" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} />
          <button type="submit">添加记录</button>
        </form>
      </section>
    </main>
  )
}
