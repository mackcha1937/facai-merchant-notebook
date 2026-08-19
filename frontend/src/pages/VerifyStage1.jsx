import { useCallback, useEffect, useState } from 'react'
import { api, yuanToCents, formatPrice } from '../api.js'

// 套餐状态与记录类型的中文显示
const PACKAGE_STATUS_LABEL = {
  active: '有效',
  exhausted: '已用完',
  inactive: '停用',
}
const ENTRY_TYPE_LABEL = {
  package_purchase: '套餐购买',
  package_consumption: '套餐核销',
  one_time_service: '一次性服务',
  product_purchase: '商品购买',
}
const TRASH_TYPE_LABEL = {
  customer: '客户',
  service: '服务项目',
  package: '套餐',
  ledger: '记录',
}

export default function VerifyStage1() {
  const [tab, setTab] = useState('customers')
  const [error, setError] = useState('')

  return (
    <main className="page">
      <h1>阶段1 验证页</h1>
      <p className="subtitle">基础账本、服务管理与回收站（不涉及自然语言/Agent）</p>

      <nav className="tabs">
        <button className={tab === 'customers' ? 'tab active' : 'tab'} onClick={() => setTab('customers')}>
          客户账本
        </button>
        <button className={tab === 'services' ? 'tab active' : 'tab'} onClick={() => setTab('services')}>
          服务项目
        </button>
        <button className={tab === 'trash' ? 'tab active' : 'tab'} onClick={() => setTab('trash')}>
          回收站
        </button>
      </nav>

      {error && (
        <div className="error-banner">
          {error}
          <button className="link" onClick={() => setError('')}>关闭</button>
        </div>
      )}

      {tab === 'customers' && <CustomersTab onError={setError} />}
      {tab === 'services' && <ServicesTab onError={setError} />}
      {tab === 'trash' && <TrashTab onError={setError} />}
    </main>
  )
}

/* ---------------- 客户账本 ---------------- */

function CustomersTab({ onError }) {
  const [customers, setCustomers] = useState([])
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null)
  const [newName, setNewName] = useState('')
  const [newAliases, setNewAliases] = useState('')

  const load = useCallback(async () => {
    try {
      setCustomers(await api.getCustomers(q))
    } catch (e) {
      onError(e.message)
    }
  }, [q, onError])

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
      onError(err.message)
    }
  }

  const removeCustomer = async (id, name) => {
    if (!window.confirm(`确定删除客户“${name}”吗？删除后会进入回收站。`)) return
    try {
      await api.deleteCustomer(id)
      setSelected(null)
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  if (selected) {
    return (
      <CustomerDetail
        customerId={selected}
        onBack={() => {
          setSelected(null)
          load()
        }}
        onError={onError}
      />
    )
  }

  return (
    <div>
      <div className="search-bar">
        <input
          placeholder="搜索客户化名或别名，如：小红 / 红姐"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      <form className="inline-form" onSubmit={createCustomer}>
        <input
          placeholder="客户化名（必填）"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        <input
          placeholder="搜索别名，多个用逗号分隔（可选）"
          value={newAliases}
          onChange={(e) => setNewAliases(e.target.value)}
        />
        <button type="submit">新增客户</button>
      </form>

      <ul className="list">
        {customers.map((c) => (
          <li key={c.id} className="list-item">
            <div className="list-item-main">
              <strong>{c.display_name}</strong>
              <span className="muted">
                {c.aliases.map((a) => a.alias).join('、') || '（无别名）'}
              </span>
            </div>
            <div className="row-actions">
              <button onClick={() => setSelected(c.id)}>查看详情</button>
              <button className="danger" onClick={() => removeCustomer(c.id, c.display_name)}>
                删除
              </button>
            </div>
          </li>
        ))}
        {customers.length === 0 && <li className="muted empty">暂无客户，请先新增。</li>}
      </ul>
    </div>
  )
}

/* ---------------- 客户详情 ---------------- */

function CustomerDetail({ customerId, onBack, onError }) {
  const [detail, setDetail] = useState(null)
  const [services, setServices] = useState([])

  // 新增套餐表单
  const [pkgService, setPkgService] = useState('')
  const [pkgTotal, setPkgTotal] = useState('')
  const [pkgPrice, setPkgPrice] = useState('')
  const [pkgDate, setPkgDate] = useState('')

  // 编辑中的套餐
  const [editingPkg, setEditingPkg] = useState(null)
  const [editTotal, setEditTotal] = useState('')
  const [editUsed, setEditUsed] = useState('')
  const [editPrice, setEditPrice] = useState('')

  // 新增记录表单
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
      onError(e.message)
    }
  }, [customerId, onError])

  useEffect(() => {
    load()
  }, [load])

  if (!detail) return <div className="muted">加载中…</div>

  const activeServices = services.filter((s) => s.status === 'active')

  const createPackage = async (e) => {
    e.preventDefault()
    if (!pkgService || !pkgTotal) {
      onError('请选择服务并填写总次数')
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
      onError(err.message)
    }
  }

  const startEdit = (p) => {
    setEditingPkg(p.id)
    setEditTotal(String(p.total_count))
    setEditUsed(String(p.used_count))
    setEditPrice(p.price_cents === null || p.price_cents === undefined ? '' : String(p.price_cents / 100))
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
      onError(err.message)
    }
  }

  const removePackage = async (p) => {
    if (!window.confirm('确定删除这张套餐卡吗？删除后会进入回收站。')) return
    try {
      await api.deletePackage(p.id)
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  const createEntry = async (e) => {
    e.preventDefault()
    const payload = {
      entry_type: entryType,
      quantity: Number(entryQty) || 1,
      price_cents: yuanToCents(entryPrice),
    }
    if (entryType === 'one_time_service') {
      payload.service_id = Number(entryService)
    } else {
      payload.product_name = entryProduct.trim()
    }
    try {
      await api.createLedger(customerId, payload)
      setEntryProduct('')
      setEntryPrice('')
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  const removeEntry = async (e) => {
    if (!window.confirm('确定删除这条记录吗？删除后会进入回收站。')) return
    try {
      await api.deleteLedger(e.id)
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  return (
    <div>
      <div className="detail-header">
        <button onClick={onBack}>← 返回列表</button>
        <h2>{detail.display_name}</h2>
        <span className="muted">
          别名：{detail.aliases.map((a) => a.alias).join('、') || '（无）'}
        </span>
      </div>

      <section className="card">
        <h3>套餐卡（剩余 = 总次数 − 已用，由后端计算）</h3>
        <ul className="list">
          {detail.packages.map((p) => (
            <li key={p.id} className="list-item column">
              {editingPkg === p.id ? (
                <div className="edit-grid">
                  <label>服务：{p.service_name}</label>
                  <label>
                    总次数
                    <input value={editTotal} onChange={(e) => setEditTotal(e.target.value)} />
                  </label>
                  <label>
                    已用次数
                    <input value={editUsed} onChange={(e) => setEditUsed(e.target.value)} />
                  </label>
                  <label>
                    价格（元）
                    <input value={editPrice} onChange={(e) => setEditPrice(e.target.value)} />
                  </label>
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
                    {p.price_cents != null && ` · 价格 ${formatPrice(p.price_cents)} 元`}
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
            {activeServices.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <input placeholder="总次数" type="number" min="1" value={pkgTotal} onChange={(e) => setPkgTotal(e.target.value)} />
          <input placeholder="价格（元，可选）" value={pkgPrice} onChange={(e) => setPkgPrice(e.target.value)} />
          <input placeholder="购买日期（可选）" value={pkgDate} onChange={(e) => setPkgDate(e.target.value)} />
          <button type="submit">新增套餐</button>
        </form>
      </section>

      <section className="card">
        <h3>消费记录（一次性服务 / 商品购买）</h3>
        <ul className="list">
          {detail.ledger.map((e) => (
            <li key={e.id} className="list-item">
              <div>
                <strong>{ENTRY_TYPE_LABEL[e.entry_type] || e.entry_type}</strong>
                <span className="muted">
                  {' '}
                  {e.entry_type === 'product_purchase' ? e.product_name : e.service_name} × {e.quantity}
                  {e.price_cents != null && ` · ${formatPrice(e.price_cents)} 元`}
                  {e.occurred_on && ` · ${e.occurred_on}`}
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
              {services.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          ) : (
            <input placeholder="商品名称" value={entryProduct} onChange={(e) => setEntryProduct(e.target.value)} />
          )}
          <input placeholder="数量" type="number" min="1" value={entryQty} onChange={(e) => setEntryQty(e.target.value)} />
          <input placeholder="价格（元，可选）" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} />
          <button type="submit">添加记录</button>
        </form>
      </section>
    </div>
  )
}

/* ---------------- 服务项目 ---------------- */

function ServicesTab({ onError }) {
  const [services, setServices] = useState([])
  const [newName, setNewName] = useState('')

  const load = useCallback(async () => {
    try {
      setServices(await api.getServices())
    } catch (e) {
      onError(e.message)
    }
  }, [onError])

  useEffect(() => {
    load()
  }, [load])

  const createService = async (e) => {
    e.preventDefault()
    try {
      await api.createService({ name: newName.trim() })
      setNewName('')
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  const toggleStatus = async (s) => {
    const next = s.status === 'active' ? 'inactive' : 'active'
    try {
      await api.updateService(s.id, { status: next })
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  const removeService = async (s) => {
    if (!window.confirm(`确定删除服务“${s.name}”吗？删除后会进入回收站。`)) return
    try {
      await api.deleteService(s.id)
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  return (
    <div>
      <form className="inline-form" onSubmit={createService}>
        <input placeholder="服务名称，如：面部清洁" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="submit">新增服务</button>
      </form>

      <ul className="list">
        {services.map((s) => (
          <li key={s.id} className="list-item">
            <div className="list-item-main">
              <strong>{s.name}</strong>
              <span className={`tag ${s.status === 'active' ? 'tag-active' : 'tag-inactive'}`}>
                {s.status === 'active' ? '启用中' : '已停用'}
              </span>
            </div>
            <div className="row-actions">
              <button onClick={() => toggleStatus(s)}>{s.status === 'active' ? '停用' : '启用'}</button>
              <button className="danger" onClick={() => removeService(s)}>删除</button>
            </div>
          </li>
        ))}
        {services.length === 0 && <li className="muted empty">暂无服务项目。</li>}
      </ul>
      <p className="footnote">停用的服务不能再用于新建套餐，但历史记录仍保留。</p>
    </div>
  )
}

/* ---------------- 回收站 ---------------- */

function TrashTab({ onError }) {
  const [items, setItems] = useState([])

  const load = useCallback(async () => {
    try {
      setItems((await api.getTrash()).items)
    } catch (e) {
      onError(e.message)
    }
  }, [onError])

  useEffect(() => {
    load()
  }, [load])

  const restore = async (item) => {
    if (!window.confirm(`确定恢复“${item.name}”吗？`)) return
    try {
      if (item.type === 'customer') await api.restoreCustomer(item.id)
      else if (item.type === 'service') await api.restoreService(item.id)
      else if (item.type === 'package') await api.restorePackage(item.id)
      else if (item.type === 'ledger') await api.restoreLedger(item.id)
      await load()
    } catch (err) {
      onError(err.message)
    }
  }

  return (
    <div>
      <ul className="list">
        {items.map((item) => (
          <li key={`${item.type}-${item.id}`} className="list-item">
            <div className="list-item-main">
              <span className={`tag tag-${item.type}`}>{TRASH_TYPE_LABEL[item.type] || item.type}</span>
              <strong>{item.name}</strong>
              <span className="muted">删除时间：{item.deleted_at ? String(item.deleted_at).slice(0, 19) : ''}</span>
            </div>
            <button onClick={() => restore(item)}>恢复</button>
          </li>
        ))}
        {items.length === 0 && <li className="muted empty">回收站为空。</li>}
      </ul>
      <p className="footnote">测试版只支持恢复，不提供永久删除。</p>
    </div>
  )
}
