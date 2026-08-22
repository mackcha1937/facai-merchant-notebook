// 双端应用壳：手机（顶部+抽屉）与电脑（左栏+主对话+右侧工作区）。
// ContextStack 统一返回闭环：详情第二层→详情第一层→列表/今日/管理→对话→关抽屉→离开应用。
import { useCallback, useEffect, useRef, useState } from 'react'
import { ContextStack, createViewContext, VIEW_TYPES } from '../../lib/contextStack.js'
import { computeTodayTaskCounts, markTaskRead } from '../../lib/todayTasks.js'
import { api } from '../../api.js'
import TopBar from '../../components/v2/TopBar.jsx'
import Drawer from '../../components/v2/Drawer.jsx'
import LeftNav from '../../components/v2/LeftNav.jsx'
import ChatView from '../v2/ChatView.jsx'
import TodayTaskCard from '../../components/v2/TodayTaskCard.jsx'
import CustomerIndexCard from '../../components/v2/CustomerIndexCard.jsx'
import CustomerRecordCard from '../../components/v2/CustomerRecordCard.jsx'
import ServiceDetailCard from '../../components/v2/ServiceDetailCard.jsx'
import ManageView from '../../components/v2/ManageView.jsx'
import ManageDetailView from '../../components/v2/ManageDetailView.jsx'
import {
  todayTaskGroups,
  mockManageGroups,
} from '../../fixtures/mock/index.js'

const makeCtx = (viewType, extra = {}) => ({ ...createViewContext({ viewType }), ...extra })

export default function AppShell({ initialView = 'chat' }) {
  const stackRef = useRef(null)
  if (stackRef.current === null) {
    let restored = null
    try { restored = JSON.parse(window.sessionStorage.getItem('facai-v2-context-stack') || 'null') } catch { restored = null }
    const canRestore = initialView === 'chat' && Array.isArray(restored) && restored.length > 0
    const stack = new ContextStack(canRestore ? restored[0] : makeCtx(VIEW_TYPES.CHAT))
    if (canRestore) {
      restored.slice(1).forEach((context) => stack.push(context))
    } else if (initialView !== 'chat') {
      stack.push(makeCtx(initialView, initialView === VIEW_TYPES.CUSTOMER_INDEX
        ? { query: '', filter: 'all', sort: 'recent_consumption', scrollPosition: 0 }
        : {}))
    }
    stackRef.current = stack
  }
  const [, setVersion] = useState(0)
  const bump = useCallback(() => setVersion((v) => v + 1), [])

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [draftInput, setDraftInput] = useState(() => window.localStorage.getItem('facai-v2-draft') || '')
  const [todayTasks, setTodayTasks] = useState([])
  const [customers, setCustomers] = useState([])
  const [records, setRecords] = useState({})
  const [serviceDetails, setServiceDetails] = useState({})
  const [dataError, setDataError] = useState('')
  const savedDraftRef = useRef('')

  const current = stackRef.current.current
  const counts = computeTodayTaskCounts(todayTasks)
  const persistStack = useCallback(() => {
    window.sessionStorage.setItem('facai-v2-context-stack', JSON.stringify(stackRef.current.snapshot()))
  }, [])

  useEffect(() => {
    window.localStorage.setItem('facai-v2-draft', draftInput)
  }, [draftInput])

  const refreshCustomers = useCallback(async () => {
    try {
      const rows = await api.getCustomers()
      setCustomers(rows.map((row) => ({ ...row, follow_up: false, unread_count: 0 })))
      setDataError('')
    } catch (error) {
      setDataError(error.message)
    }
  }, [])

  useEffect(() => { refreshCustomers() }, [refreshCustomers])

  const loadRecord = useCallback(async (customerId) => {
    try {
      const record = await api.getAuthoritativeCustomerRecord(customerId)
      setRecords((current) => ({ ...current, [customerId]: record }))
      setDataError('')
      return record
    } catch (error) {
      setDataError(error.message)
      return null
    }
  }, [])

  const mapPending = useCallback((items) => {
    setTodayTasks(items.map((item) => ({
      id: item.id,
      group: item.status === 'pending' ? 'pending' : 'conflict',
      customer_name: item.proposal.customer?.display_name || '待确认事项',
      summary: item.proposal.changes_summary || item.status,
      date: item.proposal.absolute_date || '—',
      unread: !item.read_at,
      read_at: item.read_at,
      handled_at: null,
      status: item.status,
    })))
  }, [])

  // ---- 导航（前向） ----
  const pushView = useCallback((viewType, extra = {}) => {
    if (stackRef.current.current?.viewType === VIEW_TYPES.CHAT) {
      savedDraftRef.current = draftInput
    }
    const focusCustomerId = document.activeElement?.dataset?.customerId || null
    stackRef.current.push(makeCtx(viewType, { ...extra, focusCustomerId }))
    window.history.pushState({ v2app: true, ctxDepth: stackRef.current.length - 1 }, '')
    persistStack()
    bump()
  }, [bump, draftInput, persistStack])

  const goChat = useCallback(() => {
    // 回到根层对话
    while (stackRef.current.length > 1) stackRef.current.pop()
    setDrawerOpen(false)
    setDraftInput(savedDraftRef.current)
    window.history.replaceState({ v2app: true, ctxDepth: 0 }, '')
    persistStack()
    bump()
  }, [bump, persistStack])

  const openToday = useCallback(() => pushView(VIEW_TYPES.TODAY, { scrollPosition: 0 }), [pushView])
  const openCustomerIndex = useCallback(() => pushView(VIEW_TYPES.CUSTOMER_INDEX, { query: '', filter: 'all', sort: 'recent_consumption', scrollPosition: 0 }), [pushView])
  const openManagement = useCallback(() => pushView(VIEW_TYPES.MANAGEMENT), [pushView])
  const openCustomerRecord = useCallback((customerId) => {
    pushView(VIEW_TYPES.CUSTOMER_RECORD, { customerId })
    loadRecord(customerId)
  }, [loadRecord, pushView])
  const openServiceDetail = useCallback((customerId, serviceId) => {
    pushView(VIEW_TYPES.CUSTOMER_SERVICE_DETAIL, { customerId, serviceId })
    api.getCustomerServiceDetail(customerId, serviceId)
      .then((detail) => setServiceDetails((current) => ({ ...current, [`${customerId}:${serviceId}`]: detail })))
      .catch((error) => setDataError(error.message))
  }, [pushView])
  const openManageGroup = useCallback((groupId) => pushView(VIEW_TYPES.MANAGEMENT_DETAIL, { groupId }), [pushView])

  // ---- 返回（统一顺序，按钮/浏览器返回一致） ----
  const back = useCallback(() => {
    if (stackRef.current.canGoBack()) {
      window.history.back()
      return 'pop_requested'
    }
    if (drawerOpen) {
      setDrawerOpen(false)
      return 'close_drawer'
    }
    return 'leave'
  }, [drawerOpen])

  // 浏览器返回键 / 系统返回键
  useEffect(() => {
    if (!window.history.state?.v2app) {
      window.history.replaceState({ v2app: true, ctxDepth: 0 }, '')
      for (let depth = 1; depth < stackRef.current.length; depth += 1) {
        window.history.pushState({ v2app: true, ctxDepth: depth }, '')
      }
    }
    const onPopState = (event) => {
      const targetDepth = event.state?.ctxDepth
      if (targetDepth == null) return
      let poppedContext = null
      while (stackRef.current.length - 1 > targetDepth) poppedContext = stackRef.current.pop()
      if (stackRef.current.current?.viewType === VIEW_TYPES.CHAT) setDraftInput(savedDraftRef.current)
      const focusCustomerId = poppedContext?.customerId || stackRef.current.current?.focusCustomerId
      persistStack()
      bump()
      if (focusCustomerId) {
        window.requestAnimationFrame(() => document.querySelector(`[data-customer-id="${focusCustomerId}"]`)?.focus())
      }
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [bump, persistStack])

  // ---- 导航目标 ----
  const navigateTo = useCallback((key) => {
    setDrawerOpen(false)
    if (key === 'chat') goChat()
    else if (key === 'customer_index') openCustomerIndex()
    else if (key === 'management') openManagement()
  }, [goChat, openCustomerIndex, openManagement])

  const handleTaskRead = useCallback((id) => {
    api.markPendingRead(id)
      .then(() => setTodayTasks((prev) => markTaskRead(prev, id)))
      .catch((error) => setDataError(error.message))
  }, [])
  const handleTaskHandle = useCallback(() => goChat(), [goChat])

  const handleAuthoritativeWrite = useCallback(() => {
    refreshCustomers()
    const active = stackRef.current.current
    if (active?.customerId) loadRecord(active.customerId)
  }, [loadRecord, refreshCustomers])

  const handleCustomerIndexState = useCallback((patch) => {
    const cur = stackRef.current.current
    if (cur?.viewType === VIEW_TYPES.CUSTOMER_INDEX) {
      stackRef.current.replace({
        ...cur,
        query: patch.query ?? cur.query,
        filter: patch.filter ?? cur.filter,
        sort: patch.sort ?? cur.sort,
        scrollPosition: patch.scrollPosition ?? cur.scrollPosition,
      })
      persistStack()
      bump()
    }
  }, [bump, persistStack])

  useEffect(() => {
    const active = stackRef.current.current
    if (active?.customerId && !records[active.customerId]) loadRecord(active.customerId)
  }, [current?.customerId, loadRecord, records])

  // ---- 渲染当前工作区视图 ----
  const renderView = () => {
    switch (current.viewType) {
      case VIEW_TYPES.TODAY:
        return (
          <TodayTaskCard
            tasks={todayTasks}
            groupLabels={todayTaskGroups}
            onRead={handleTaskRead}
            onHandle={handleTaskHandle}
            onBack={back}
            savedScroll={current.scrollPosition || 0}
            onScrollChange={(pos) => { current.scrollPosition = pos }}
          />
        )
      case VIEW_TYPES.CUSTOMER_INDEX:
        return (
          <CustomerIndexCard
            customers={customers}
            onOpenCustomer={(c) => openCustomerRecord(c.id)}
            onBack={back}
            saved={{ query: current.query, filter: current.filter, sort: current.sort, scrollPosition: current.scrollPosition }}
            onStateChange={handleCustomerIndexState}
          />
        )
      case VIEW_TYPES.CUSTOMER_RECORD: {
        const record = records[current.customerId]
        return (
          record ? <CustomerRecordCard
            record={record}
            onBackToList={back}
            onOpenService={(sid) => openServiceDetail(current.customerId, sid)}
          /> : <div className="v2-state">正在读取最新权威客户档案…</div>
        )
      }
      case VIEW_TYPES.CUSTOMER_SERVICE_DETAIL: {
        const record = records[current.customerId]
        const service = serviceDetails[`${current.customerId}:${current.serviceId}`]
        return service
          ? <ServiceDetailCard service={service} customerName={record?.display_name || '客户'} onBack={back} />
          : <div className="v2-state">正在读取最新权威服务数据…</div>
      }
      case VIEW_TYPES.MANAGEMENT:
        return <ManageView onBack={back} onOpenGroup={(g) => openManageGroup(g.id)} />
      case VIEW_TYPES.MANAGEMENT_DETAIL:
        return <ManageDetailView group={mockManageGroups.find((g) => g.id === current.groupId)} onBack={back} />
      case VIEW_TYPES.CHAT:
      default:
        return null
    }
  }

  const contextView = renderView()
  const activeKey = current.viewType === VIEW_TYPES.CHAT ? 'chat'
    : current.viewType === VIEW_TYPES.CUSTOMER_INDEX ? 'customer_index'
      : current.viewType === VIEW_TYPES.MANAGEMENT || current.viewType === VIEW_TYPES.MANAGEMENT_DETAIL ? 'management'
        : ''

  return (
    <div className="v2-shell" data-testid="app-shell">
      <TopBar
        onMenu={() => setDrawerOpen(true)}
        onToday={openToday}
        unresolvedCount={counts.unresolved_count}
        unreadCount={counts.unread_count}
      />

      <div className="v2-shell-body">
        <LeftNav active={activeKey} onNavigate={navigateTo} />

        <main className="v2-center">
          {dataError && <div className="v2-inline-error">{dataError}</div>}
          <ChatView
            draftInput={draftInput}
            onDraftChange={setDraftInput}
            onPendingChange={mapPending}
            onAuthoritativeWrite={handleAuthoritativeWrite}
          />
        </main>

        {contextView && (
          <aside className="v2-right open" data-testid="right-workspace">
            {contextView}
          </aside>
        )}
      </div>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} onNavigate={navigateTo} active={activeKey} />
    </div>
  )
}
