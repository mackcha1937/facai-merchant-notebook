import { describe, it, expect } from 'vitest'
import { computeTodayTaskCounts, markTaskRead, handleTask, groupTasks } from '../lib/todayTasks.js'
import { mockTodayTasks, todayTaskGroups } from '../fixtures/mock/index.js'

describe('今日事项数字与红点规则', () => {
  it('unresolved_count=未处理数，unread_count=未查看数', () => {
    const { unresolved_count, unread_count } = computeTodayTaskCounts(mockTodayTasks)
    expect(unresolved_count).toBe(4)
    expect(unread_count).toBe(4)
  })

  it('打开总列表不清除全部红点（不提供批量清空）', () => {
    // 模拟“打开列表”不改变任何任务
    const still = mockTodayTasks.map((t) => ({ ...t }))
    expect(computeTodayTaskCounts(still).unread_count).toBe(4)
  })

  it('只成功打开某一条后才更新该条 read_at，其他红点保留', () => {
    const updated = markTaskRead(mockTodayTasks, 't1')
    expect(updated.find((t) => t.id === 't1').unread).toBe(false)
    expect(updated.find((t) => t.id === 't1').read_at).toBeTruthy()
    expect(updated.filter((t) => t.unread).length).toBe(3)
  })

  it('查看（read）不等于处理（handled），处理后未处理数才下降', () => {
    const read = markTaskRead(mockTodayTasks, 't1')
    expect(computeTodayTaskCounts(read).unresolved_count).toBe(4) // 只看不处理，未处理数不变
    const handled = handleTask(read, 't1')
    expect(computeTodayTaskCounts(handled).unresolved_count).toBe(3)
    expect(handled.find((t) => t.id === 't1').handled_at).toBeTruthy()
  })

  it('按四个分组归类', () => {
    const groups = groupTasks(mockTodayTasks, todayTaskGroups)
    expect(Object.keys(groups).sort()).toEqual(['待确认', '冲突', '建议跟进', '资料待补充'].sort())
  })
})
