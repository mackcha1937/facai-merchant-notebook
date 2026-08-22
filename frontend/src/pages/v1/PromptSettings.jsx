import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api.js'

export default function PromptSettings() {
  const [current, setCurrent] = useState(null)
  const [versions, setVersions] = useState([])
  const [content, setContent] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)

  const [testText, setTestText] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const load = useCallback(async () => {
    try {
      const [cur, vers] = await Promise.all([api.getPrompt(), api.getPromptVersions()])
      setCurrent(cur)
      setContent(cur.content)
      setVersions(vers)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const saveNew = async () => {
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const saved = await api.savePromptVersion(content)
      setNotice(`已保存为新版本 v${saved.version}（尚未激活）`)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const activate = async (id) => {
    if (!window.confirm('确定激活这个版本吗？激活后后续解析将使用该版本。')) return
    try {
      await api.activatePromptVersion(id)
      setNotice('已切换版本')
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  const runTest = async () => {
    if (!testText.trim()) { setError('请输入试运行文本'); return }
    setTesting(true)
    setError('')
    setTestResult(null)
    try {
      const data = await api.interpret(testText)
      setTestResult(data)
      if (data.error) setError(data.error)
    } catch (e) {
      setError(e.message)
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <div className="v1-sheet">
        <div className="v1-sheet-handle" />
        <div className="v1-sheet-body">
          <div className="v1-sheet-title">
            <h2>系统提示词管理</h2>
          </div>
          <p className="v1-hint">
            当前模型 ID：{current ? current.model_id : '…'}（不会显示 API Key）
          </p>

          {error && <div className="v1-error-banner">{error}</div>}
          {notice && <div className="v1-notice">{notice}</div>}

          <div className="v1-section-head"><strong>当前激活提示词（v{current ? current.version : '…'}）</strong></div>
          <textarea
            className="v1-textarea"
            rows={16}
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="v1-row-actions" style={{ marginTop: 10 }}>
            <button className="v1-btn" onClick={saveNew} disabled={saving}>{saving ? '保存中…' : '保存为新版本'}</button>
            <span className="v1-muted">保存不会立即生效，需在下方手动激活。</span>
          </div>

          <div className="v1-section-head"><strong>版本历史</strong></div>
          <div className="v1-history">
            {versions.map((v) => (
              <div key={v.id} className="v1-history-item">
                <span className="v1-history-icon">v{v.version}</span>
                <span className="v1-history-main">
                  <strong>{v.is_active ? '当前激活' : `版本 v${v.version}`}</strong>
                  <span>{v.created_at ? String(v.created_at).slice(0, 19) : ''}</span>
                </span>
                <span className="v1-row-actions">
                  <button className="v1-link-btn" onClick={() => setContent(v.content)}>查看</button>
                  {!v.is_active && <button className="v1-link-btn" onClick={() => activate(v.id)}>激活</button>}
                </span>
              </div>
            ))}
          </div>

          <div className="v1-section-head"><strong>试运行（仅解析，不写入）</strong></div>
          <textarea
            className="v1-textarea"
            rows={2}
            placeholder="例如：阿珍今天买了一盒面膜。"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
          />
          <div className="v1-row-actions" style={{ marginTop: 10 }}>
            <button className="v1-btn secondary" onClick={runTest} disabled={testing}>{testing ? '解析中…' : '试运行'}</button>
          </div>
          {testResult && !testResult.error && (
            <p className="v1-hint" style={{ marginTop: 8 }}>
              识别客户：{testResult.customer_query}（{testResult.customer_match?.status}）
              · 操作 {testResult.actions?.length} 项 · 提示词版本 v{testResult.prompt_version}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
