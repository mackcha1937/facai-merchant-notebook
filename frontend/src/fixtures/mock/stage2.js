// 阶段2 Mock 数据（全部 is_mock=true，不读取/展示真实客户姓名、手机号、微信名）
// 只用于 /app/* 和 /verify/v2-stage-2 演示；不混入真实 SQLite 业务表。

export const isMock = true

// 化名客户（演示用）
export const mockCustomers = [
  {
    id: 'c1',
    display_name: '阿珍',
    aliases: ['珍姐', '阿珍姐'],
    is_mock: true,
    service_type_count: 4,
    last_consumed_at: '2026-08-20',
    last_consumed_service_name: '面部清洁',
    follow_up: true,
    unread_count: 1,
  },
  {
    id: 'c2',
    display_name: '小美',
    aliases: ['美美'],
    is_mock: true,
    service_type_count: 2,
    last_consumed_at: '2026-08-15',
    last_consumed_service_name: '肩颈按摩',
    follow_up: false,
    unread_count: 0,
  },
  {
    id: 'c3',
    display_name: '王姐',
    aliases: ['王女士'],
    is_mock: true,
    service_type_count: 5,
    last_consumed_at: '2026-08-10',
    last_consumed_service_name: '深层补水',
    follow_up: true,
    unread_count: 0,
  },
  {
    id: 'c4',
    display_name: '李阿姨',
    aliases: [],
    is_mock: true,
    service_type_count: 1,
    last_consumed_at: '2026-07-28',
    last_consumed_service_name: '肩颈按摩',
    follow_up: false,
    unread_count: 0,
  },
  {
    id: 'c5',
    display_name: '陈女士',
    aliases: ['陈姐'],
    is_mock: true,
    service_type_count: 3,
    last_consumed_at: '2026-08-18',
    last_consumed_service_name: '面部清洁',
    follow_up: true,
    unread_count: 0,
  },
]

// 客户完整档案（CustomerRecordCard 分区演示）
export const mockCustomerRecord = {
  id: 'c1',
  display_name: '阿珍',
  aliases: ['珍姐', '阿珍姐'],
  is_mock: true,
  overview: {
    since: '2025-11-02',
    total_consumption_count: 26,
    total_spend_cents: 128000,
    service_type_count: 4,
    active_package_count: 2,
  },
  facts: [
    { id: 'f1', type: '敏感肤质', value: '敏感肌，避免高浓度酸类', confidence: 0.92, confirmed: true, is_mock: true },
    { id: 'f2', type: '偏好', value: '喜欢柑橘香，不接受浓香', confidence: 0.85, confirmed: true, is_mock: true },
    { id: 'f3', type: '禁忌', value: '孕期，停用功效类产品', confidence: 0.95, confirmed: true, is_mock: true },
  ],
  services: [
    { id: 's1', name: '面部清洁', service_type_count: 3, last_consumed_at: '2026-08-20', total_remaining_count: 5, is_mock: true },
    { id: 's2', name: '肩颈按摩', service_type_count: 2, last_consumed_at: '2026-08-10', total_remaining_count: 0, is_mock: true },
    { id: 's3', name: '深层补水', service_type_count: 1, last_consumed_at: '2026-08-01', total_remaining_count: null, is_mock: true },
    { id: 's4', name: '手部护理', service_type_count: 1, last_consumed_at: '2026-07-12', total_remaining_count: 2, is_mock: true },
  ],
  products: [
    { id: 'p1', name: '舒缓保湿霜', last_purchased_at: '2026-08-20', purchase_count: 3, is_mock: true },
    { id: 'p2', name: '氨基酸洁面乳', last_purchased_at: '2026-08-05', purchase_count: 2, is_mock: true },
  ],
  follow_ups: [
    { id: 'fu1', type: '建议跟进', summary: '套餐剩余5次，建议本月回访', date: '2026-08-25', is_mock: true },
    { id: 'fu2', type: '待确认', summary: '上次提到想加手部护理套餐', date: '2026-08-22', is_mock: true },
  ],
  ledger_history: [
    { id: 'l1', entry_type: 'package_consumption', name: '面部清洁', occurred_on: '2026-08-20', quantity: 1, is_mock: true },
    { id: 'l2', entry_type: 'product_purchase', name: '舒缓保湿霜', occurred_on: '2026-08-20', quantity: 1, is_mock: true },
    { id: 'l3', entry_type: 'one_time_service', name: '肩颈按摩', occurred_on: '2026-08-10', quantity: 1, is_mock: true },
  ],
}

// 产品匹配演示（ProductMatchCard 五种状态）
export const mockProductMatches = {
  exact: {
    status: 'exact',
    matched: { id: 'p1', name: '舒缓保湿霜', brand: '品牌A', spec: '50ml', is_mock: true },
  },
  fuzzy: {
    status: 'fuzzy',
    matched: { id: 'p1', name: '舒缓保湿霜', brand: '品牌A', spec: '50ml', is_mock: true },
  },
  ambiguous: {
    status: 'ambiguous',
    candidates: [
      { id: 'p1', name: '舒缓保湿霜', brand: '品牌A', spec: '50ml', is_mock: true },
      { id: 'p2', name: '舒缓保湿乳', brand: '品牌A', spec: '30ml', is_mock: true },
      { id: 'p3', name: '舒缓保湿精华', brand: '品牌B', spec: '30ml', is_mock: true },
    ],
  },
  not_found: {
    status: 'not_found',
    recognized: { name: '某某品牌修护面膜', is_mock: true },
  },
  insufficient: {
    status: 'insufficient',
    recognized: { name: '补水', is_mock: true },
  },
}

// 今日事项（Mock，含 read_at/handled_at/status）
export const mockTodayTasks = [
  {
    id: 't1',
    group: 'suggested_follow_up',
    type: '建议跟进',
    customer_name: '阿珍',
    summary: '面部清洁套餐剩5次，建议本周回访',
    date: '2026-08-25',
    unread: true,
    read_at: null,
    handled_at: null,
    status: 'new',
    is_mock: true,
  },
  {
    id: 't2',
    group: 'pending_confirm',
    type: '待确认',
    customer_name: '陈女士',
    summary: '“她说月底再问一次”待确认下次提醒日期',
    date: '2026-08-24',
    unread: true,
    read_at: null,
    handled_at: null,
    status: 'new',
    is_mock: true,
  },
  {
    id: 't3',
    group: 'material_required',
    type: '资料待补充',
    customer_name: '王姐',
    summary: '新产品“某某修护面膜”缺规格与品牌',
    date: '2026-08-23',
    unread: true,
    read_at: null,
    handled_at: null,
    status: 'new',
    is_mock: true,
  },
  {
    id: 't4',
    group: 'conflict',
    type: '冲突',
    customer_name: '小美',
    summary: '“敏感肌”与历史“中性肌”冲突，需确认',
    date: '2026-08-22',
    unread: true,
    read_at: null,
    handled_at: null,
    status: 'new',
    is_mock: true,
  },
]

// 对话演示消息（Mock，展示各类固定 UI Block）
export const mockChatMessages = [
  { id: 'm1', role: 'assistant', kind: 'text', text: '下午好～今天想记点什么？', is_mock: true },
  { id: 'm2', role: 'user', kind: 'text', text: '阿珍今天面部清洁1次，还买了舒缓保湿霜', is_mock: true },
  { id: 'm3', role: 'assistant', kind: 'text', text: '好的，我先核对一下，确认后才会写入账本。', is_mock: true },
]

// 今日事项分组标题
export const todayTaskGroups = {
  suggested_follow_up: '建议跟进',
  pending_confirm: '待确认',
  material_required: '资料待补充',
  conflict: '冲突',
}

// 管理与设置分组（店主端只读闭环）
export const mockManageGroups = [
  { id: 'products_services', label: '产品与服务', is_mock: true },
  { id: 'data_management', label: '数据管理', is_mock: true },
  { id: 'account_security', label: '账号与安全', is_mock: true },
  { id: 'ai_status', label: 'AI运行状态（只读）', is_mock: true },
]

// AI 运行状态（只读，不含 API Key / 提示词全文 / 阈值权重）
export const mockAiStatus = {
  is_mock: true,
  chat_model: { id: 'deepseek-v4-pro', status: '可用（Mock）' },
  embedding: { status: '未接入（阶段2不接Embedding）' },
  rag: { status: '未接入' },
  recommendation: { status: '未接入' },
  last_check_at: '2026-08-22 10:00',
}

// 语音 Mock 演示语句（点击语音后可选择“说了什么”）
export const mockSpeechUtterances = [
  '返回客户列表',
  '日期改成昨天',
  '取消',
  '王姐今天做了一次肩颈按摩',
]
