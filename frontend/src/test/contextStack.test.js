import { describe, it, expect } from 'vitest'
import { ContextStack, createViewContext, VIEW_TYPES } from '../lib/contextStack.js'

describe('ContextStack 逐层返回', () => {
  it('从根层开始，根层为对话', () => {
    const s = new ContextStack(createViewContext({ viewType: VIEW_TYPES.CHAT }))
    expect(s.current.viewType).toBe('chat')
    expect(s.canGoBack()).toBe(false)
  })

  it('push 后 canGoBack 为真，pop 回到上一层', () => {
    const s = new ContextStack(createViewContext({ viewType: VIEW_TYPES.CHAT }))
    s.push(createViewContext({ viewType: VIEW_TYPES.CUSTOMER_INDEX }))
    s.push(createViewContext({ viewType: VIEW_TYPES.CUSTOMER_RECORD, customerId: 'c1' }))
    s.push(createViewContext({ viewType: VIEW_TYPES.CUSTOMER_SERVICE_DETAIL, customerId: 'c1', serviceId: 's1' }))
    expect(s.current.viewType).toBe('customer_service_detail')
    s.pop()
    expect(s.current.viewType).toBe('customer_record')
    s.pop()
    expect(s.current.viewType).toBe('customer_index')
    s.pop()
    expect(s.current.viewType).toBe('chat')
    expect(s.canGoBack()).toBe(false)
  })

  it('保存 query/filter/sort/scroll/draft 字段', () => {
    const s = new ContextStack(createViewContext({ viewType: VIEW_TYPES.CHAT, draftInput: '草稿' }))
    s.push(createViewContext({ viewType: VIEW_TYPES.CUSTOMER_INDEX, query: '珍', filters: { follow_up: true }, sort: 'recent_consumption', scrollPosition: 120, draftInput: '' }))
    const cur = s.current
    expect(cur.query).toBe('珍')
    expect(cur.filters).toEqual({ follow_up: true })
    expect(cur.sort).toBe('recent_consumption')
    expect(cur.scrollPosition).toBe(120)
  })

  it('根层 pop 返回 null，不破坏根层', () => {
    const s = new ContextStack(createViewContext({ viewType: VIEW_TYPES.CHAT }))
    expect(s.pop()).toBeNull()
    expect(s.current.viewType).toBe('chat')
  })
})
