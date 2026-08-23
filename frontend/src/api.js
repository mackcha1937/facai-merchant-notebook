// 后端 API 调用封装（通过 Vite 代理访问，相对路径）
async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = `请求失败（HTTP ${res.status}）`
    let payload = null
    try {
      payload = await res.json()
      if (payload && payload.detail) detail = payload.detail
    } catch (e) {
      /* 忽略解析错误 */
    }
    const error = new Error(detail)
    error.status = res.status
    error.payload = payload
    throw error
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // 阶段3持续主会话与统一 Proposal
  getMainThread: () => request('/api/owner/chat/thread'),
  getChatHistory: ({ before, limit = 30 } = {}) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (before) params.set('before', String(before))
    return request(`/api/owner/chat/history?${params}`)
  },
  getPendingActions: () => request('/api/owner/chat/pending'),
  sendChatTurn: (data) => request('/api/owner/chat/turn', { method: 'POST', body: JSON.stringify(data) }),
  streamChatTurn: async (data, onEvent = () => {}) => {
    const res = await fetch('/api/owner/chat/turn/stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    })
    if (!res.ok) {
      let payload = null
      try { payload = await res.json() } catch { payload = null }
      const error = new Error(payload?.detail || `请求失败（HTTP ${res.status}）`)
      error.status = res.status
      error.payload = payload
      throw error
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult = null
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split('\n\n')
      buffer = frames.pop() || ''
      for (const frame of frames) {
        const event = frame.match(/^event:\s*(.+)$/m)?.[1]
        const raw = frame.match(/^data:\s*(.+)$/m)?.[1]
        if (!event || !raw) continue
        const payload = JSON.parse(raw)
        onEvent(event, payload)
        if (event === 'validated_block') finalResult = payload
      }
    }
    return finalResult
  },
  markMessageRead: (id) => request(`/api/owner/messages/${id}/read`, { method: 'POST' }),
  markPendingRead: (id) => request(`/api/owner/pending/${id}/read`, { method: 'POST' }),
  confirmStage3Proposal: (id, data) => request(`/api/owner/proposals/${id}/confirm`, { method: 'POST', body: JSON.stringify(data) }),
  cancelStage3Proposal: (id, data) => request(`/api/owner/proposals/${id}/cancel`, { method: 'POST', body: JSON.stringify(data) }),
  editStage3Proposal: (id, data) => request(`/api/owner/proposals/${id}/edit`, { method: 'POST', body: JSON.stringify(data) }),
  regenerateStage3Proposal: (id, data) => request(`/api/owner/proposals/${id}/regenerate`, { method: 'POST', body: JSON.stringify(data) }),
  getAuthoritativeCustomerRecord: (id) => request(`/api/owner/customers/${id}/record`),
  getStage3Status: () => request('/api/v2-stage3/status'),
  // 阶段4客户事实与产品实体（所有写入仍返回统一 Proposal）
  resolveProduct: (data) => request('/api/owner/products/resolve', { method: 'POST', body: JSON.stringify(data) }),
  getProducts: () => request('/api/owner/products'),
  getProduct: (id) => request(`/api/owner/products/${id}`),
  createProductDraftProposal: (data) => request('/api/owner/products/draft-proposal', { method: 'POST', body: JSON.stringify(data) }),
  createProductMergeProposal: (data) => request('/api/owner/products/merge-proposal', { method: 'POST', body: JSON.stringify(data) }),

  // 阶段5知识链路：店主只读证据；管理员发布治理
  getStage5Status: () => request('/api/v2-stage5/status'),
  getOwnerKnowledgeStatus: () => request('/api/owner/knowledge/status'),
  getOwnerKnowledge: () => request('/api/owner/knowledge'),
  retrieveKnowledge: (data) => request('/api/owner/knowledge/retrieve', { method: 'POST', body: JSON.stringify(data) }),
  getAdminKnowledge: () => request('/api/admin/knowledge'),
  createAdminKnowledgeProposal: (data) => request('/api/admin/knowledge/proposals', { method: 'POST', body: JSON.stringify(data) }),
  createAdminKnowledgeWithdrawProposal: (data) => request('/api/admin/knowledge/withdraw-proposals', { method: 'POST', body: JSON.stringify(data) }),
  confirmAdminKnowledgeProposal: (id, data) => request(`/api/admin/knowledge/proposals/${id}/confirm`, { method: 'POST', body: JSON.stringify(data) }),
  reindexKnowledge: (entityType, entityId) => request(`/api/admin/knowledge/${entityType}/${entityId}/reindex`, { method: 'POST' }),
  createCustomerFactProposal: (customerId, data) => request(`/api/owner/customers/${customerId}/facts/proposal`, { method: 'POST', body: JSON.stringify(data) }),
  resolveProposalProduct: (id, data) => request(`/api/owner/proposals/${id}/resolve-product`, { method: 'POST', body: JSON.stringify(data) }),
  getStage4Status: () => request('/api/v2-stage4/status'),
  // 客户
  getCustomers: (search) =>
    request(`/api/customers${search ? `?search=${encodeURIComponent(search)}` : '?sort=last_consumed_desc'}`),
  getCustomer: (id) => request(`/api/customers/${id}`),
  getCustomerOverview: (id) => request(`/api/customers/${id}/overview`),
  getCustomerServices: (id) => request(`/api/customers/${id}/services`),
  getCustomerServiceDetail: (id, serviceId) =>
    request(`/api/customers/${id}/services/${serviceId}`),
  createCustomer: (data) =>
    request('/api/customers', { method: 'POST', body: JSON.stringify(data) }),
  updateCustomer: (id, data) =>
    request(`/api/customers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCustomer: (id) => request(`/api/customers/${id}`, { method: 'DELETE' }),
  restoreCustomer: (id) =>
    request(`/api/customers/${id}/restore`, { method: 'POST' }),
  searchFuzzy: (query) =>
    request('/api/customers/search-fuzzy', { method: 'POST', body: JSON.stringify({ query }) }),

  // 服务
  getServices: () => request('/api/services'),
  createService: (data) =>
    request('/api/services', { method: 'POST', body: JSON.stringify(data) }),
  updateService: (id, data) =>
    request(`/api/services/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteService: (id) => request(`/api/services/${id}`, { method: 'DELETE' }),
  restoreService: (id) =>
    request(`/api/services/${id}/restore`, { method: 'POST' }),

  // 套餐
  createPackage: (cid, data) =>
    request(`/api/customers/${cid}/packages`, { method: 'POST', body: JSON.stringify(data) }),
  updatePackage: (id, data) =>
    request(`/api/packages/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePackage: (id) => request(`/api/packages/${id}`, { method: 'DELETE' }),
  restorePackage: (id) =>
    request(`/api/packages/${id}/restore`, { method: 'POST' }),

  // 账本记录
  createLedger: (cid, data) =>
    request(`/api/customers/${cid}/ledger`, { method: 'POST', body: JSON.stringify(data) }),
  deleteLedger: (id) => request(`/api/ledger/${id}`, { method: 'DELETE' }),
  restoreLedger: (id) => request(`/api/ledger/${id}/restore`, { method: 'POST' }),

  // 回收站
  getTrash: () => request('/api/trash'),

  // Agent 解析（阶段2：只生成建议，不写入）
  interpret: (text) =>
    request('/api/agent/interpret', { method: 'POST', body: JSON.stringify({ text }) }),
  getProposal: (id) => request(`/api/agent/proposals/${id}`),
  cancelProposal: (id) => request(`/api/agent/proposals/${id}/cancel`, { method: 'POST' }),
  confirmProposal: (id, data) =>
    request(`/api/agent/proposals/${id}/confirm`, { method: 'POST', body: JSON.stringify(data) }),
  precheckProposal: (id, data) =>
    request(`/api/agent/proposals/${id}/precheck`, { method: 'POST', body: JSON.stringify(data) }),

  // 提示词管理
  getPrompt: () => request('/api/settings/prompt'),
  getPromptVersions: () => request('/api/settings/prompt/versions'),
  savePromptVersion: (content) =>
    request('/api/settings/prompt/versions', { method: 'POST', body: JSON.stringify({ content }) }),
  activatePromptVersion: (id) =>
    request(`/api/settings/prompt/versions/${id}/activate`, { method: 'POST' }),
}

// 元 -> 分（价格存储单位是“分”）
export function yuanToCents(v) {
  if (v === '' || v === null || v === undefined) return null
  const n = Number(v)
  if (Number.isNaN(n)) return null
  return Math.round(n * 100)
}

// 分 -> 元（用于显示）
export function formatPrice(cents) {
  if (cents === null || cents === undefined) return '—'
  const yuan = cents / 100
  return Number.isInteger(yuan) ? String(yuan) : yuan.toFixed(2)
}
