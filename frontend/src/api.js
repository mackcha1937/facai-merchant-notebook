// 后端 API 调用封装（通过 Vite 代理访问，相对路径）
async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = `请求失败（HTTP ${res.status}）`
    try {
      const data = await res.json()
      if (data && data.detail) detail = data.detail
    } catch (e) {
      /* 忽略解析错误 */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // 客户
  getCustomers: (q) =>
    request(`/api/customers${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  getCustomer: (id) => request(`/api/customers/${id}`),
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
