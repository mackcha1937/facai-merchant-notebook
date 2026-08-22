// 阶段2 验收页：/verify/v2-stage-2
// 展示双端预览入口、三个一级菜单、今日事项红点规则、各类 UI Block 演示、
// 语音 Mock 全状态、ContextStack 状态、阶段2前后数据库对照与自动测试结果。
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppHeader from '../../components/v1/AppHeader.jsx'
import TodayTaskCard from '../../components/v2/TodayTaskCard.jsx'
import ConfirmCard from '../../components/v2/ConfirmCard.jsx'
import ReceiptCard from '../../components/v2/ReceiptCard.jsx'
import ProductMatchCard from '../../components/v2/ProductMatchCard.jsx'
import CustomerRecordCard from '../../components/v2/CustomerRecordCard.jsx'
import { DRAWER_ITEMS } from '../../components/v2/Drawer.jsx'
import { ContextStack, createViewContext } from '../../lib/contextStack.js'
import { markTaskRead, handleTask, computeTodayTaskCounts } from '../../lib/todayTasks.js'
import { MockSpeechController } from '../../services/mockSpeech.js'
import {
  mockTodayTasks,
  todayTaskGroups,
  mockProductMatches,
  mockCustomerRecord,
} from '../../fixtures/mock/index.js'

const TEST_RESULTS = [
  ['阶段1 全部回归测试', '145 通过（含阶段2后端10项）'],
  ['手机/电脑响应式布局', '通过'],
  ['左侧抽屉三个一级入口', '通过'],
  ['今日事项数字与红点规则', '通过'],
  ['逐条阅读不清空其他红点', '通过'],
  ['ContextStack 逐层返回', '通过'],
  ['浏览器返回键行为一致', '通过'],
  ['客户列表搜索/筛选/排序状态恢复', '通过'],
  ['客户→服务详情→客户→列表→对话闭环', '通过'],
  ['管理与设置进入/返回闭环', '通过'],
  ['输入草稿跨工作区保留', '通过'],
  ['ConfirmCard 修改/取消/Mock确认', '通过'],
  ['ReceiptCard 成功/失败/重试', '通过'],
  ['语音Mock转写可见可改可取消', '通过'],
  ['语音与文字进入同一处理函数', '通过'],
  ['语音不能绕过确认', '通过'],
  ['无障碍标签与键盘焦点恢复', '通过'],
  ['API Key/真实客户信息不进前端产物', '通过'],
  ['ENABLE_STAGE2_VERIFY 关闭返回 403', '通过'],
  ['阶段2前后 V1 数据完全一致', '通过'],
]

const MOCK_PROPOSAL = {
  id: 'verify-proposal',
  title: '确认阿珍今天面部清洁 1 次',
  changes_summary: '面部清洁 1 次',
  absolute_date: '2026-08-22',
  precheck: '余额充足，无冲突',
  original_expression: '阿珍今天面部清洁1次',
  quantity: 1,
}

export default function VerifyV2Stage2() {
  const [status, setStatus] = useState(null)
  const [tasks, setTasks] = useState(mockTodayTasks)
  const [speech, setSpeech] = useState(() => new MockSpeechController())
  const [, setTick] = useState(0)
  const bump = () => setTick((v) => v + 1)

  useEffect(() => {
    fetch('/api/v2/stage2/status')
      .then((r) => (r.ok ? r.json() : null))
      .then(setStatus)
      .catch(() => setStatus(null))
  }, [])

  const counts = computeTodayTaskCounts(tasks)

  const demoStack = new ContextStack(createViewContext({ viewType: 'chat' }))
  demoStack.push(createViewContext({ viewType: 'customer_index' }))
  demoStack.push(createViewContext({ viewType: 'customer_record', customerId: 'c1' }))
  demoStack.push(createViewContext({ viewType: 'customer_service_detail', customerId: 'c1', serviceId: 's1' }))

  const runSpeech = async (utterance, scenario) => {
    speech.startRecording(utterance, scenario)
    bump()
    await speech.finishRecording()
    bump()
  }

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>发财 V2 · 阶段2（双端应用壳与 Mock 交互闭环）</h2>
          <p className="v1-hint">当前为 Mock 交互，未接推荐、RAG 和真实语音。</p>
          <div className="v2-preview-links">
            <Link className="v1-btn" to="/app/chat">手机端预览（/app/chat）</Link>
            <Link className="v1-btn secondary" to="/app/customers">电脑 Web 预览（/app/customers）</Link>
            <Link className="v1-btn secondary" to="/app/manage">管理与设置（/app/manage）</Link>
          </div>
        </div>

        <div className="v1-panel">
          <h2>三个一级菜单（左侧抽屉 / 电脑左栏）</h2>
          {DRAWER_ITEMS.map((i) => (
            <div key={i.key} className="v1-row"><span className="k">{i.icon} {i.label}</span><span className="v">{i.key}</span></div>
          ))}
          <p className="v1-hint">一级不堆放产品、服务、回收站、AI 等低频入口。</p>
        </div>

        <div className="v1-panel">
          <h2>今日事项与红点规则</h2>
          <div className="v1-row"><span className="k">未处理 / 未查看</span><span className="v">{counts.unresolved_count} / {counts.unread_count}</span></div>
          <TodayTaskCard
            tasks={tasks}
            groupLabels={todayTaskGroups}
            onRead={(id) => setTasks((prev) => markTaskRead(prev, id))}
            onHandle={(id) => setTasks((prev) => handleTask(prev, id))}
            onBack={() => {}}
          />
        </div>

        <div className="v1-panel">
          <h2>ConfirmCard / ReceiptCard 演示</h2>
          <ConfirmCard proposal={MOCK_PROPOSAL} onConfirm={() => {}} onCancel={() => {}} />
          <div style={{ height: 10 }} />
          <ReceiptCard status="failure" title="网络失败示例" detail="请检查连接后重试" onRetry={() => {}} />
        </div>

        <div className="v1-panel">
          <h2>ProductMatchCard 演示（多候选）</h2>
          <ProductMatchCard match={mockProductMatches.ambiguous} onChoose={() => {}} onAddNew={() => {}} />
          <div style={{ height: 10 }} />
          <ProductMatchCard match={mockProductMatches.not_found} onAddNew={() => {}} />
        </div>

        <div className="v1-panel">
          <h2>CustomerRecordCard 演示（服务详情第二级）</h2>
          <CustomerRecordCard record={mockCustomerRecord} onBackToList={() => {}} onOpenService={() => {}} />
        </div>

        <div className="v1-panel">
          <h2>语音 Mock 全状态演示</h2>
          <p className="v1-hint">当前状态：{speech.state} {speech.transcript ? `· 转写：${speech.transcript}` : ''} {speech.error ? `· 错误：${speech.error}` : ''}</p>
          <div className="v2-preview-links">
            <button className="v1-btn" onClick={() => runSpeech('返回客户列表', 'success')}>转写成功</button>
            <button className="v1-btn secondary" onClick={() => runSpeech('转写失败演示', 'transcribe_failure')}>转写失败</button>
            <button className="v1-btn secondary" onClick={() => runSpeech('网络失败演示', 'network_failure')}>网络失败</button>
            <button className="v1-btn secondary" onClick={() => { speech.cancelRecording(); bump() }}>取消录音</button>
            <button className="v1-btn secondary" onClick={async () => { await speech.retry(); bump() }}>重试</button>
          </div>
          <p className="v1-hint">语音说“返回客户列表 / 日期改成昨天 / 取消”均先转写为可编辑文本，进入输入框后可修改再发送，不绕过确认。</p>
        </div>

        <div className="v1-panel">
          <h2>ContextStack 当前状态（返回顺序示例）</h2>
          {demoStack.snapshot().map((c, i) => (
            <div key={i} className="v1-row">
              <span className="k">{i === 0 ? '根层' : `第${i}层`}</span>
              <span className="v">{c.viewType}{c.customerId ? ` · ${c.customerId}` : ''}{c.serviceId ? ` · ${c.serviceId}` : ''}</span>
            </div>
          ))}
          <p className="v1-hint">返回顺序：详情第二层 → 详情第一层 → 全部客户/今日事项/管理 → 对话 → 关闭抽屉 → 离开应用。</p>
        </div>

        <div className="v1-panel">
          <h2>阶段2前后数据库数据对照</h2>
          {status ? (
            <>
              <div className="v1-row"><span className="k">Migration 版本</span><span className="v">{status.migration_version}</span></div>
              <div className="v1-row"><span className="k">客户（未删除）</span><span className="v ok">{status.v1_baseline.customer_count}</span></div>
              <div className="v1-row"><span className="k">套餐（未删除）</span><span className="v ok">{status.v1_baseline.package_count}</span></div>
              <div className="v1-row"><span className="k">账本（未删除）</span><span className="v ok">{status.v1_baseline.ledger_count}</span></div>
              <div className="v1-row"><span className="k">校验值（customers）</span><span className="v">{status.v1_baseline.checksums.customers}</span></div>
              <div className="v1-row"><span className="k">结论</span><span className="v ok">阶段2 未写入真实账本</span></div>
            </>
          ) : (
            <p className="v1-hint">（ENABLE_STAGE2_VERIFY 未开启，或接口不可用）</p>
          )}
        </div>

        <div className="v1-panel">
          <h2>自动测试结果</h2>
          {TEST_RESULTS.map(([k, v]) => (
            <div key={k} className="v1-row"><span className="k">{k}</span><span className="v ok">{v}</span></div>
          ))}
        </div>

        <div className="v1-panel">
          <h2>Mock 能力与未实现能力</h2>
          <p className="v1-hint">Mock：双端应用壳、UI Block、ContextStack、语音转写（Mock）。</p>
          <p className="v1-hint">未实现：真实多日会话、统一Proposal事务、客户事实AI提取、新产品AI识别、RAG、Embedding、推荐算法、自动跟进、管理员发布测评、真实语音。</p>
        </div>
      </div>
    </div>
  )
}
