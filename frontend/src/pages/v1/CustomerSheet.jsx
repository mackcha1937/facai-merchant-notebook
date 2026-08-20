import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, yuanToCents, formatPrice } from '../../api.js'

function formatDate(iso) {
  if (!iso) return '未记录'
  const [y, m, d] = String(iso).slice(0, 10).split('-')
  return `${y}年${Number(m)}月${Number(d)}日`
}

const ENTRY_LABEL = {
  package_consumption: '套餐核销',
  one_time_service: '一次性服务',
  product_purchase: '商品购买',
  package_purchase: '套餐购买',
}

export default function CustomerSheet() {
  const [view, setView] = useState('list') // list | overview | service
  const [customers, setCustomers] = useState([])
  const [search, setSearch] = useState('')
  const [customerId, setCustomerId] = useState(null)
  const [overview, setOverview] = useState(null)
  const [serviceId, setServiceId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')

  const loadCustomers = useCallback(async () => {
    try {
      setCustomers(await api.getCustomers(search))
    } catch (e) {
      setError(e.message)
    }
  }, [search])

  useEffect(() => {
    loadCustomers()
  }, [loadCustomers])

  const openOverview = async (id) => {
    setError('')
    try {
      const data = await api.getCustomerOverview(id)
      setCustomerId(id)
      setOverview(data)
      setView('overview')
    } catch (e) {
      setError(e.message)
    }
  }

  const openService = async (sid) => {
    setError('')
    try {
      const data = await api.getCustomerServiceDetail(customerId, sid)
      setServiceId(sid)
      setDetail(data)
      setView('service')
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="v1-app">
      <div className="v1-sheet">
        <div className="v1-sheet-handle" />
        <div className="v1-sheet-body">
          {error && <div className="v1-error-banner">{error}</div>}

          {view === 'list' && (
            <CustomerList
              customers={customers}
              search={search}
              setSearch={setSearch}
              onOpen={openOverview}
              onReload={loadCustomers}
              onError={setError}
            />
          )}
          {view === 'overview' && overview && (
            <CustomerOverview
              overview={overview}
              onBack={() => setView('list')}
              onOpenService={openService}
            />
          )}
          {view === 'service' && detail && (
            <ServiceDetailView
              detail={detail}
              onBack={() => setView('overview')}
              onReload={() => openService(serviceId)}
              onError={setError}
            />
          )}
        </div>
      </div>
      <div className="v1-sheet-close-row">
        <Link to="/" className="v1-btn secondary">关闭账本</Link>
      </div>
    </div>
  )
}

function CustomerList({ customers, search, setSearch, onOpen, onReload, onError }) {
  const [showAdd, setShowAdd] = useState(false)
  const [name, setName] = useState('')
  const [aliases, setAliases] = useState('')

  const addCustomer = async (e) => {
    e.preventDefault()
    try {
      await api.createCustomer({
        display_name: name.trim(),
        aliases: aliases.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
      })
      setName('')
      setAliases('')
      setShowAdd(false)
      await onReload()
    } catch (err) {
      onError(err.message)
    }
  }

  return (
    <>
      <div className="v1-sheet-title">
        <h2>客户账本</h2>
        <button className="v1-btn secondary" onClick={() => setShowAdd(!showAdd)}>＋ 新增客户</button>
      </div>

      {showAdd && (
        <form className="v1-inline-form" onSubmit={addCustomer}>
          <input placeholder="客户化名（必填）" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="别名，逗号分隔" value={aliases} onChange={(e) => setAliases(e.target.value)} />
          <button className="v1-btn" type="submit">保存</button>
        </form>
      )}

      <div className="v1-search">
        <span>⌕</span>
        <input placeholder="搜索客户或别名" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="v1-customer-list">
        {customers.map((c) => (
          <button key={c.id} className="v1-customer-item" onClick={() => onOpen(c.id)}>
            <span className="v1-avatar">{c.display_name.slice(0, 1)}</span>
            <span className="v1-customer-main">
              <span className="v1-customer-name">{c.display_name}{c.aliases.length > 0 && ` · ${c.aliases.join('、')}`}</span>
              <span className="v1-customer-note">
                {c.last_consumed_service_name
                  ? <>最近：{c.last_consumed_service_name} · {formatDate(c.last_consumed_at)}</>
                  : '暂无消费记录'}
              </span>
            </span>
            <span className="v1-customer-balance">
              <strong>{c.service_type_count}类</strong>服务 ›
            </span>
          </button>
        ))}
        {customers.length === 0 && <div className="v1-state"><span>☐</span><span>暂无客户，请新增。</span></div>}
      </div>
    </>
  )
}

function CustomerOverview({ overview, onBack, onOpenService }) {
  return (
    <>
      <div className="v1-sheet-title">
        <button className="v1-back" onClick={onBack}>← 返回客户列表</button>
      </div>
      <div className="v1-detail-head">
        <span className="v1-avatar">{overview.display_name.slice(0, 1)}</span>
        <div>
          <h2>{overview.display_name}</h2>
          <p>别名：{overview.aliases.join('、') || '无'} · 最近消费 {formatDate(overview.last_consumed_at)}</p>
        </div>
      </div>
      <div className="v1-stats">
        <div className="v1-stat"><span>服务类型</span><strong>{overview.service_type_count}类</strong></div>
        <div className="v1-stat"><span>有效套餐</span><strong>{overview.active_package_count}个</strong></div>
      </div>

      <div className="v1-section-head"><strong>全部服务</strong></div>
      <div className="v1-service-list">
        {overview.services.map((s) => (
          <button key={s.service_id} className="v1-service-item" onClick={() => onOpenService(s.service_id)}>
            <span className="v1-service-icon">{s.service_name.slice(0, 1)}</span>
            <span className="v1-service-main">
              <strong>{s.service_name}</strong>
              <span>最近消费：{formatDate(s.last_consumed_at)}</span>
            </span>
            <span className="v1-service-summary">
              <strong>
                {s.is_one_time_only ? '一次性' : s.total_remaining_count != null ? `剩余${s.total_remaining_count}` : '—'}
              </strong>
              查看详情 ›
            </span>
          </button>
        ))}
      </div>

      <div className="v1-section-head"><strong>最近动态</strong></div>
      <div className="v1-history">
        {overview.recent_entries.map((e) => (
          <div key={e.id} className="v1-history-item">
            <span className="v1-history-icon">{e.entry_type === 'product_purchase' ? '＋' : '−'}</span>
            <span className="v1-history-main">
              <strong>{e.service_name || e.product_name}</strong>
              <span>{formatDate(e.occurred_on)} · {ENTRY_LABEL[e.entry_type] || e.entry_type}</span>
            </span>
            <span className="v1-history-count">{e.quantity}次</span>
          </div>
        ))}
        {overview.recent_entries.length === 0 && <div className="v1-state"><span>暂无动态</span></div>}
      </div>
    </>
  )
}

function ServiceDetailView({ detail, onBack, onReload, onError }) {
  const [showAddPkg, setShowAddPkg] = useState(false)
  const [pkgTotal, setPkgTotal] = useState('')
  const [pkgPrice, setPkgPrice] = useState('')
  const [showAddEntry, setShowAddEntry] = useState(false)
  const [entryType, setEntryType] = useState('one_time_service')
  const [entryPackage, setEntryPackage] = useState('')
  const [entryQty, setEntryQty] = useState('1')
  const [entryPrice, setEntryPrice] = useState('')

  const addPackage = async (e) => {
    e.preventDefault()
    try {
      await api.createPackage(detail.customer_id, {
        service_id: detail.service_id,
        total_count: Number(pkgTotal),
        price_cents: yuanToCents(pkgPrice),
      })
      setPkgTotal('')
      setPkgPrice('')
      setShowAddPkg(false)
      await onReload()
    } catch (err) {
      onError(err.message)
    }
  }

  const addEntry = async (e) => {
    e.preventDefault()
    const payload = {
      entry_type: entryType,
      quantity: Number(entryQty) || 1,
      price_cents: yuanToCents(entryPrice),
    }
    if (entryType === 'package_consumption') payload.package_id = Number(entryPackage)
    else payload.service_id = detail.service_id
    try {
      await api.createLedger(detail.customer_id, payload)
      setEntryQty('1')
      setEntryPrice('')
      setShowAddEntry(false)
      await onReload()
    } catch (err) {
      onError(err.message)
    }
  }

  const removePackage = async (p) => {
    if (!window.confirm(`确定删除这张「${detail.service_name}」套餐卡吗？`)) return
    try {
      await api.deletePackage(p.id)
      await onReload()
    } catch (err) {
      onError(err.message)
    }
  }

  const removeEntry = async (e) => {
    if (!window.confirm('确定删除这条记录吗？删除后余额会自动重算。')) return
    try {
      await api.deleteLedger(e.id)
      await onReload()
    } catch (err) {
      onError(err.message)
    }
  }

  return (
    <>
      <div className="v1-sheet-title">
        <button className="v1-back" onClick={onBack}>← 返回{detail.customer_display_name}的服务</button>
      </div>
      <div className="v1-detail-head">
        <span className="v1-service-icon">{detail.service_name.slice(0, 1)}</span>
        <div>
          <h2>{detail.service_name}</h2>
          <p>最近消费：{formatDate(detail.last_consumed_at)}</p>
        </div>
      </div>

      <div className="v1-section-head">
        <strong>套餐详情</strong>
        <button className="v1-btn secondary" onClick={() => setShowAddPkg(!showAddPkg)}>＋ 新增套餐</button>
      </div>
      {showAddPkg && (
        <form className="v1-inline-form" onSubmit={addPackage}>
          <input placeholder="总次数" type="number" min="1" value={pkgTotal} onChange={(e) => setPkgTotal(e.target.value)} />
          <input placeholder="价格（元，可选）" value={pkgPrice} onChange={(e) => setPkgPrice(e.target.value)} />
          <button className="v1-btn" type="submit">保存</button>
        </form>
      )}
      <div className="v1-package-list">
        {detail.packages.map((p) => (
          <div key={p.id} className="v1-package-card">
            <div className="v1-package-top">
              <div>
                <strong>{detail.service_name}</strong>
                <span> {p.total_count}次套餐{p.price_cents != null && ` · ¥${formatPrice(p.price_cents)}`}</span>
              </div>
              <div className="v1-package-number">{p.remaining_count}/{p.total_count}</div>
            </div>
            <div className="v1-progress"><i style={{ width: `${Math.min(100, (p.used_count / p.total_count) * 100)}%` }} /></div>
            <div className="v1-package-foot">
              <span>已使用{p.used_count}次</span>
              <span>剩余{p.remaining_count}次</span>
              <button className="v1-link-btn" onClick={() => removePackage(p)}>删除</button>
            </div>
          </div>
        ))}
        {detail.packages.length === 0 && (
          <div className="v1-package-card">
            <div className="v1-package-top">
              <div><strong>{detail.service_name}</strong><span> 一次性服务，不计算套餐余额</span></div>
              <div className="v1-package-number">单次</div>
            </div>
          </div>
        )}
      </div>

      <div className="v1-section-head">
        <strong>该服务记录</strong>
        <button className="v1-btn secondary" onClick={() => setShowAddEntry(!showAddEntry)}>＋ 记一笔</button>
      </div>
      {showAddEntry && (
        <form className="v1-inline-form" onSubmit={addEntry}>
          <select value={entryType} onChange={(e) => setEntryType(e.target.value)}>
            <option value="one_time_service">一次性服务</option>
            {detail.packages.length > 0 && <option value="package_consumption">套餐核销</option>}
          </select>
          {entryType === 'package_consumption' ? (
            <select value={entryPackage} onChange={(e) => setEntryPackage(e.target.value)}>
              <option value="">选择套餐卡…</option>
              {detail.packages.map((p) => (
                <option key={p.id} value={p.id}>卡#{p.id}（剩{p.remaining_count}）</option>
              ))}
            </select>
          ) : (
            <span className="v1-muted">服务：{detail.service_name}</span>
          )}
          <input placeholder="次数" type="number" min="1" value={entryQty} onChange={(e) => setEntryQty(e.target.value)} />
          <input placeholder="价格（元，可选）" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} />
          <button className="v1-btn" type="submit">保存</button>
        </form>
      )}
      <div className="v1-history">
        {detail.history.map((e) => (
          <div key={e.id} className="v1-history-item">
            <span className="v1-history-icon">{e.entry_type === 'package_consumption' ? '−' : '·'}</span>
            <span className="v1-history-main">
              <strong>{e.entry_type === 'package_consumption' ? '套餐核销' : '一次性服务'}</strong>
              <span>{formatDate(e.occurred_on)} · {e.quantity}次{e.price_cents != null && ` · ¥${formatPrice(e.price_cents)}`}</span>
            </span>
            <button className="v1-link-btn" onClick={() => removeEntry(e)}>删除</button>
          </div>
        ))}
        {detail.history.length === 0 && <div className="v1-state"><span>暂无记录</span></div>}
      </div>
    </>
  )
}
