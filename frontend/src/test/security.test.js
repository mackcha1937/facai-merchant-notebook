import { describe, it, expect } from 'vitest'
import {
  mockCustomers,
  mockCustomerRecord,
  mockTodayTasks,
  mockProductMatches,
  mockAiStatus,
} from '../fixtures/mock/index.js'

// 阶段2 Mock 数据安全：不出现 API Key、手机号、微信标识；所有对象标记 is_mock。
const phoneRe = /1[3-9]\d{9}/
const keyRe = /sk-[A-Za-z0-9]{8,}|DEEPSEEK_API_KEY|api[_-]?key/i

function collectStrings(obj, acc = []) {
  if (obj == null) return acc
  if (typeof obj === 'string') { acc.push(obj); return acc }
  if (Array.isArray(obj)) { obj.forEach((x) => collectStrings(x, acc)); return acc }
  if (typeof obj === 'object') { Object.values(obj).forEach((x) => collectStrings(x, acc)); return acc }
  return acc
}

describe('Mock 数据安全与标记', () => {
  it('所有 Mock 客户/记录/事项标记 is_mock=true', () => {
    mockCustomers.forEach((c) => expect(c.is_mock).toBe(true))
    expect(mockCustomerRecord.is_mock).toBe(true)
    mockTodayTasks.forEach((t) => expect(t.is_mock).toBe(true))
  })

  it('Mock 数据不包含手机号/微信标识/API Key', () => {
    const strings = collectStrings({ mockCustomers, mockCustomerRecord, mockTodayTasks, mockProductMatches, mockAiStatus })
    for (const s of strings) {
      expect(phoneRe.test(s)).toBe(false)
      expect(keyRe.test(s)).toBe(false)
    }
  })
})
