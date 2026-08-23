import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'

const EMPTY_RELEASES = { prompt: [], rag: [], recommendation: [] }
const makeKey = (prefix) => `${prefix}-${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`}`

export default function AdminEvaluations() {
  const [drafts, setDrafts] = useState([])
  const [runs, setRuns] = useState([])
  const [releases, setReleases] = useState(EMPTY_RELEASES)
  const [audits, setAudits] = useState([])
  const [type, setType] = useState('recommendation')
  const [content, setContent] = useState('{"policy_version":"stage7-local-v1"}')
  const [csvText, setCsvText] = useState('')
  const [confirmations, setConfirmations] = useState({})
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const operationKeys = useRef({})

  const refresh = useCallback(() => Promise.all([
    api.getEvaluationDrafts(), api.getEvaluationRuns(), api.getEvaluationReleases(), api.getEvaluationAudits(),
  ]).then(([draftRows, runRows, releaseRows, auditRows]) => {
    setDrafts(draftRows); setRuns(runRows); setReleases(releaseRows); setAudits(auditRows); setError('')
  }).catch((failure) => setError(failure.message)), [])

  useEffect(() => { refresh() }, [refresh])
  const draftsById = useMemo(() => Object.fromEntries(drafts.map((row) => [row.id, row])), [drafts])

  const keyFor = (scope) => {
    if (!operationKeys.current[scope]) operationKeys.current[scope] = makeKey(scope)
    return operationKeys.current[scope]
  }

  const perform = async (key, operation, success, idempotencyScope = null) => {
    setBusy(key); setError(''); setNotice('')
    try {
      const result = await operation()
      setNotice(typeof success === 'function' ? success(result) : success)
      if (idempotencyScope) {
        delete operationKeys.current[idempotencyScope]
        delete operationKeys.current[`${idempotencyScope}-request`]
      }
      await refresh()
    }
    catch (failure) { setError(failure.message) }
    finally { setBusy('') }
  }

  const create = () => perform('create', async () => {
    await api.createEvaluationDraft({ config_type: type, content: JSON.parse(content) })
  }, '草稿已创建；尚未发布。')

  const run = (draftId) => {
    const scope = `stage7-run-${draftId}`
    perform(`run-${draftId}`, () => api.startEvaluationRun({
      draft_id: draftId, idempotency_key: keyFor(scope),
    }), '已载入60条JSONL用例；未执行项保持阻塞，不能发布。', scope)
  }

  const importCsv = (runId) => perform(
    `import-${runId}`,
    () => api.importEvaluationWorkbook(runId, csvText),
    (result) => `人工结果已导入：门禁 ${result.summary.gate_status}`,
  )

  const publish = (runRow) => {
    const draft = draftsById[runRow.draft_id]
    if (!draft) return
    const scope = `stage7-publish-${runRow.id}`
    perform(`publish-${runRow.id}`, () => api.publishEvaluationRelease({
      draft_id: draft.id,
      run_id: runRow.id,
      confirmation: confirmations[`publish-${runRow.id}`] || '',
      expected_data_version: draft.data_version,
      request_id: keyFor(`${scope}-request`),
      idempotency_key: keyFor(scope),
    }), `配置草稿 #${draft.id} 已发布。`, scope)
  }

  const rollback = (releaseType, release) => {
    const scope = `stage7-rollback-${releaseType}-${release.id}`
    perform(`rollback-${releaseType}-${release.id}`, () => api.rollbackEvaluationRelease({
      release_type: releaseType,
      release_id: release.id,
      confirmation: confirmations[`rollback-${releaseType}-${release.id}`] || '',
      request_id: keyFor(`${scope}-request`),
      idempotency_key: keyFor(scope),
    }), `${releaseType} 已回滚到上一版本。`, scope)
  }

  return <main className="page stage7-admin" style={{ maxWidth: 1050 }}>
    <section className="card"><h1>阶段7 · AI测评与管理员发布</h1>
      <p className="hint">完全离线：JSONL快照、CSV工作簿往返、安全与质量门槛、二次确认发布及回滚。未真实执行的用例绝不记为通过。</p>
      <p><Link to="/verify/v2-stage-7">查看阶段7验收页</Link></p></section>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {notice && <div className="notice-banner" role="status">{notice}</div>}

    <section className="card"><h2>1. 配置草稿</h2>
      <label>类型<select value={type} onChange={(event) => setType(event.target.value)}><option value="prompt">Prompt</option><option value="rag">RAG</option><option value="recommendation">推荐策略</option></select></label>
      <label>配置JSON<textarea rows="5" value={content} onChange={(event) => setContent(event.target.value)} /></label>
      <button disabled={Boolean(busy)} onClick={create}>创建草稿</button>
      {drafts.map((row) => <div className="list-item" key={row.id}><span>#{row.id} · {row.config_type} · {row.status} · v{row.data_version} · {row.checksum.slice(0, 10)}</span><button disabled={Boolean(busy) || row.status === 'published'} onClick={() => run(row.id)}>运行离线测评</button></div>)}
    </section>

    <section className="card"><h2>2. 测评Run与人工工作簿</h2>
      <p className="hint">导出CSV可用Excel填写；必须完整回导60条、四项评分均为1～5。所有用例通过、安全关键100%，且四项均分都不低于4.0才允许发布。</p>
      <label>CSV回填内容<textarea rows="7" value={csvText} onChange={(event) => setCsvText(event.target.value)} placeholder="case_id,passed,factual,safety,natural,interaction,notes" /></label>
      {runs.map((row) => {
        const draft = draftsById[row.draft_id]
        const expected = draft ? `PUBLISH-${draft.id}-${draft.checksum.slice(0, 8)}` : ''
        const canPublish = Boolean(row.summary.release_allowed && draft?.status === 'evaluated')
        return <div className="list-item column" key={row.id}><strong>Run #{row.id} · {row.summary.gate_status}</strong>
          <span>通过 {row.summary.passed}/{row.summary.total} · 失败 {row.summary.failed} · 阻塞 {row.summary.blocked} · 安全 {row.summary.safety_passed}/{row.summary.safety_total}</span>
          <span>人工均分：事实 {row.summary.manual_averages?.factual ?? '-'} / 安全 {row.summary.manual_averages?.safety ?? '-'} / 自然 {row.summary.manual_averages?.natural ?? '-'} / 交互 {row.summary.manual_averages?.interaction ?? '-'}</span>
          <div className="row-actions"><a href={`/api/admin/evaluations/runs/${row.id}/workbook.csv`}>导出CSV工作簿</a><button disabled={Boolean(busy) || !csvText.trim()} onClick={() => importCsv(row.id)}>导入完整结果</button></div>
          <label>发布二次确认<input aria-label={`Run ${row.id} 发布确认`} disabled={!canPublish} value={confirmations[`publish-${row.id}`] || ''} onChange={(event) => setConfirmations((current) => ({ ...current, [`publish-${row.id}`]: event.target.value }))} placeholder={canPublish ? expected : '门槛通过且草稿未发布时开放'} /></label>
          <button disabled={Boolean(busy) || !canPublish || confirmations[`publish-${row.id}`] !== expected} onClick={() => publish(row)}>发布已测评版本</button>
        </div>
      })}
    </section>

    <section className="card"><h2>3. 发布与回滚</h2>
      <p className="hint">页面不展示Key、配置正文或强行跳过按钮。回滚只恢复同类上一发布版本，不修改历史账本。</p>
      {Object.entries(releases).map(([releaseType, rows]) => <div key={releaseType}><h3>{releaseType}</h3>
        {rows.length === 0 && <p className="hint">暂无发布版本</p>}
        {rows.map((row) => <div className="list-item column" key={`${releaseType}-${row.id}`}><strong>v{row.version} · {row.status}</strong><span>Release #{row.id} · Run #{row.evaluation_run_id ?? '-'}</span>
          {row.rollback_confirmation && <><label>回滚二次确认<input aria-label={`${releaseType} ${row.id} 回滚确认`} value={confirmations[`rollback-${releaseType}-${row.id}`] || ''} onChange={(event) => setConfirmations((current) => ({ ...current, [`rollback-${releaseType}-${row.id}`]: event.target.value }))} placeholder={row.rollback_confirmation} /></label><button disabled={Boolean(busy) || confirmations[`rollback-${releaseType}-${row.id}`] !== row.rollback_confirmation} onClick={() => rollback(releaseType, row)}>回滚上一版本</button></>}
        </div>)}
      </div>)}
    </section>

    <section className="card"><h2>4. 发布审计</h2>
      {audits.length === 0 ? <p className="hint">暂无发布或回滚审计</p> : audits.map((row) => <div className="list-item" key={row.id}><span>#{row.id} · {row.release_type} · {row.action} · Release #{row.release_id}</span><time>{row.created_at}</time></div>)}
    </section>
  </main>
}
