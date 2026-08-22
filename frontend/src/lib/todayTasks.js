// 今日事项纯逻辑（可独立测试）。
// 规则：
// - unresolved_count = 未处理数（handled_at 为空）
// - unread_count = 未查看数（unread === true）
// - 打开总列表不清除全部红点；
// - 只有成功打开某一条后，才更新该条 read_at；
// - 查看（read）不等于处理（handled），处理后未处理数才下降。

export function computeTodayTaskCounts(tasks) {
  const unresolved_count = tasks.filter((t) => !t.handled_at).length
  const unread_count = tasks.filter((t) => t.unread).length
  return { unresolved_count, unread_count }
}

export function markTaskRead(tasks, taskId) {
  return tasks.map((t) => {
    if (t.id !== taskId || !t.unread) return t
    return { ...t, unread: false, read_at: new Date().toISOString() }
  })
}

export function handleTask(tasks, taskId, status = 'contacted') {
  return tasks.map((t) => {
    if (t.id !== taskId) return t
    return { ...t, handled_at: new Date().toISOString(), status }
  })
}

export function groupTasks(tasks, groupLabel) {
  const groups = {}
  for (const t of tasks) {
    const key = t.group || 'other'
    const label = groupLabel[key] || key
    if (!groups[label]) groups[label] = []
    groups[label].push(t)
  }
  return groups
}
