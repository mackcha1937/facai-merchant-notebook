// 双端应用壳：手机（顶部+抽屉）与电脑（左栏+主对话+右侧工作区）。
// ContextStack 统一返回闭环：详情第二层→详情第一层→列表/今日/管理→对话→关抽屉→离开应用。
import { useCallback, useEffect, useRef, useState } from 'react'
import { ContextStack, createViewContext, VIEW_TYPES } from '../../lib/contextStack.js'
import { computeTodayTaskCounts, markTaskRead, handleTask } from '../../lib/todayTasks.js'
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
  mockCustomers,
  mockCustomerRecord,
  mockTodayTasks,
  todayTaskGroups,
  mockManageGroups,
} from '../../fixtures/mock/index.js'

const makeCtx = (viewType, extra = {}) => ({ ...createViewContext({ viewType }), ...extra })

function getRecord(customerId) {
  const customer = mockCustomers.find((c) => c.id === customerId)
  if (customerId === 'c1') return mockCustomerRecord
  return {
    ...mockCustomerRecord,
    id: customerId,
    display_name: customer?.display_name || '客户',
    aliases: customer?.aliases || [],
  }
}

export default function AppShell({ initialView = 'chat' }) {
  const stackRef = useRef(null)
  if (stackRef.current === null) {
    const stack = new ContextStack(makeCtx(VIEW_TYPES.CHAT))
    if (initialView !== 'chat') {
      stack.push(makeCtx(initialView, initialView === VIEW_TYPES.CUSTOMER_INDEX
        ? { query: '', filter: 'all', sort: 'recent_consumption', scrollPosition: 0 }
        : {}))
    }
    stackRef.current = stack
  }
  const [, setVersion] = useState(0)
  const bump = useCallback(() => setVersion((v) => v + 1), [])

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [draftInput, setDraftInput] = useState('')
  const [sending, setSending] = useState(false)
  const [todayTasks, setTodayTasks] = useState(mockTodayTasks)
  const savedDraftRef = useRef('')

  const current = stackRef.current.current
  const counts = computeTodayTaskCounts(todayTasks)

  // ---- 导航（前向） ----
  const pushView = useCallback((viewType, extra = {}) => {
    if (stackRef.current.current?.viewType === VIEW_TYPES.CHAT) {
      savedDraftRef.current = draftInput
    }
    stackRef.current.push(makeCtx(viewType, extra))
    bump()
  }, [bump, draftInput])

  const goChat = useCallback(() => {
    // 回到根层对话
    while (stackRef.current.length > 1) stackRef.current.pop()
    setDrawerOpen(false)
    setDraftInput(savedDraftRef.current)
    bump()
  }, [bump])

  const openToday = useCallback(() => pushView(VIEW_TYPES.TODAY, { scrollPosition: 0 }), [pushView])
  const openCustomerIndex = useCallback(() => pushView(VIEW_TYPES.CUSTOMER_INDEX, { query: '', filter: 'all', sort: 'recent_consumption', scrollPosition: 0 }), [pushView])
  const openManagement = useCallback(() => pushView(VIEW_TYPES.MANAGEMENT), [pushView])
  const openCustomerRecord = useCallback((customerId) => pushView(VIEW_TYPES.CUSTOMER_RECORD, { customerId }), [pushView])
  const openServiceDetail = useCallback((customerId, serviceId) => pushView(VIEW_TYPES.CUSTOMER_SERVICE_DETAIL, { customerId, serviceId }), [pushView])
  const openManageGroup = useCallback((groupId) => pushView(VIEW_TYPES.MANAGEMENT_DETAIL, { groupId }), [pushView])

  // ---- 返回（统一顺序，按钮/浏览器返回一致） ----
  const back = useCallback(() => {
    if (stackRef.current.canGoBack()) {
      stackRef.current.pop()
      if (stackRef.current.current?.viewType === VIEW_TYPES.CHAT) {
        setDraftInput(savedDraftRef.current)
      }
      bump()
      return 'pop'
    }
    if (drawerOpen) {
      setDrawerOpen(false)
      return 'close_drawer'
    }
    return 'leave'
  }, [bump, drawerOpen])

  // 浏览器返回键 / 系统返回键
  useEffect(() => {
    if (!window.history.state?.v2app) {
      window.history.replaceState({ v2app: true }, '')
    }
    const onPopState = () => {
      const action = back()
      if (action !== 'leave') {
        // 内部返回，重新压入一个历史条目，保持应用在栈内
        window.history.pushState({ v2app: true }, '')
      }
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [back])

  // ---- 导航目标 ----
  const navigateTo = useCallback((key) => {
    setDrawerOpen(false)
    if (key === 'chat') goChat()
    else if (key === 'customer_index') openCustomerIndex()
    else if (key === 'management') openManagement()
  }, [goChat, openCustomerIndex, openManagement])

  const handleSend = useCallback((text) => {
    setSending(true)
    // Mock 生成：稍后停止（可随时点停止）
    window.setTimeout(() => setSending(false), 1500)
  }, [])

  const handleStop = useCallback(() => setSending(false), [])

  const handleTaskRead = useCallback((id) => setTodayTasks((prev) => markTaskRead(prev, id)), [])
  const handleTaskHandle = useCallback((id) => setTodayTasks((prev) => handleTask(prev, id)), [])

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
      bump()
    }
  }, [bump])

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
            customers={mockCustomers}
            onOpenCustomer={(c) => openCustomerRecord(c.id)}
            onBack={back}
            saved={{ query: current.query, filter: current.filter, sort: current.sort, scrollPosition: current.scrollPosition }}
            onStateChange={handleCustomerIndexState}
          />
        )
      case VIEW_TYPES.CUSTOMER_RECORD: {
        const record = getRecord(current.customerId)
        return (
          <CustomerRecordCard
            record={record}
            onBackToList={back}
            onOpenService={(sid) => openServiceDetail(current.customerId, sid)}
          />
        )
      }
      case VIEW_TYPES.CUSTOMER_SERVICE_DETAIL: {
        const record = getRecord(current.customerId)
        const service = record.services.find((s) => s.id === current.serviceId)
        return <ServiceDetailCard service={service} customerName={record.display_name} onBack={back} />
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
          <ChatView
            draftInput={draftInput}
            onDraftChange={setDraftInput}
            sending={sending}
            onSend={handleSend}
            onStop={handleStop}
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
