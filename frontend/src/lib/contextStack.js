// 统一 ContextStack（纯逻辑，可独立测试）。
// 保存：viewType / originType / originMessageId / parentBlockId /
//       query / filters / sort / scrollPosition / draftInput
// 返回顺序由 AppShell 调用方保证：
//   详情第二层 → 详情第一层 → 全部客户/今日事项/管理 → 对话 → 关闭抽屉 → 离开应用

export const VIEW_TYPES = {
  CHAT: 'chat',
  TODAY: 'today',
  CUSTOMER_INDEX: 'customer_index',
  CUSTOMER_RECORD: 'customer_record',
  CUSTOMER_SERVICE_DETAIL: 'customer_service_detail',
  MANAGEMENT: 'management',
  MANAGEMENT_DETAIL: 'management_detail',
}

export function createViewContext({
  viewType,
  originType = 'chat',
  originMessageId = null,
  parentBlockId = null,
  query = '',
  filters = {},
  sort = 'recent',
  scrollPosition = 0,
  draftInput = '',
}) {
  return {
    viewType,
    originType,
    originMessageId,
    parentBlockId,
    query,
    filters,
    sort,
    scrollPosition,
    draftInput,
  }
}

export class ContextStack {
  constructor(root = null) {
    this.stack = root ? [root] : []
  }

  get length() {
    return this.stack.length
  }

  get root() {
    return this.stack[0] || null
  }

  get current() {
    return this.stack[this.stack.length - 1] || null
  }

  push(ctx) {
    this.stack.push(ctx)
    return this.current
  }

  pop() {
    if (this.stack.length <= 1) return null
    return this.stack.pop()
  }

  replace(ctx) {
    this.stack[this.stack.length - 1] = ctx
    return this.current
  }

  canGoBack() {
    return this.stack.length > 1
  }

  snapshot() {
    return this.stack.map((c) => ({ ...c }))
  }
}
