export default function App() {
  return (
    <main className="page">
      <h1>美容店智能客户账本 MVP</h1>
      <p className="subtitle">本地测试版 · 当前进度：阶段3（自然语言记账与查询闭环）</p>
      <section className="card">
        <p>
          <a href="/verify/stage-3">打开阶段3验证页（输入→解析→确认→写入）</a>
        </p>
        <p>
          <a href="/verify/stage-2">打开阶段2验证页（仅解析）</a>
        </p>
        <p>
          <a href="/settings/prompt">系统提示词管理</a>
        </p>
        <p>
          <a href="/verify/stage-1">打开阶段1验证页（客户/服务/回收站）</a>
        </p>
        <p>
          <a href="/verify/stage-0">打开阶段0验证页（骨架与模型连通性）</a>
        </p>
      </section>
    </main>
  )
}
