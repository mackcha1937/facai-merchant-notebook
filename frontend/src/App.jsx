export default function App() {
  return (
    <main className="page">
      <h1>美容店智能客户账本 MVP</h1>
      <p className="subtitle">本地测试版 · 阶段4（联调与本地验收）</p>
      <section className="card">
        <p>
          <a href="/verify/stage-4">阶段4 验收总览（推荐入口）</a>
        </p>
        <p>
          <a href="/verify/stage-3">自然语言记账（输入→解析→确认→写入）</a>
        </p>
        <p>
          <a href="/verify/stage-1">客户账本（客户/服务/回收站）</a>
        </p>
        <p>
          <a href="/settings/prompt">系统提示词管理</a>
        </p>
        <p>
          <a href="/verify/stage-2">自然语言解析（仅解析）</a>
        </p>
        <p>
          <a href="/verify/stage-0">骨架与模型连通性</a>
        </p>
      </section>
    </main>
  )
}
