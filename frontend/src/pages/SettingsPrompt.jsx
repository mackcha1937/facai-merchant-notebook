import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

export default function SettingsPrompt() {
  const [current, setCurrent] = useState(null)
  const [versions, setVersions] = useState([])
  const [content, setContent] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)

  // 试运行
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

  useEffect(() => {
    load()
  }, [load])

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
    setError('')
    setNotice('')
    try {
      await api.activatePromptVersion(id)
      setNotice('已切换版本')
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  const runTest = async () => {
    if (!testText.trim()) {
      setError('请输入试运行文本')
      return
    }
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
    <main className="page">
      <h1>系统提示词管理</h1>
      <p className="subtitle">
        当前模型 ID：{current ? current.model_id : '…'}
        <span className="muted">（不会显示 API Key）</span>
      </p>

      {error && <div className="error-banner">{error}</div>}
      {notice && <div className="notice-banner">{notice}</div>}

      <section className="card">
        <h2>当前激活提示词（v{current ? current.version : '…'}）</h2>
        <textarea
          className="input-area mono"
          rows={18}
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
        <div className="row-actions" style={{ marginTop: 10 }}>
          <button onClick={saveNew} disabled={saving}>
            {saving ? '保存中…' : '保存为新版本'}
          </button>
          <span className="muted">保存不会立即生效，需在下方手动激活。</span>
        </div>
      </section>

      <section className="card">
        <h2>版本历史</h2>
        <ul className="list">
          {versions.map((v) => (
            <li key={v.id} className="list-item">
              <div className="list-item-main">
                <span className="tag tag-customer">v{v.version}</span>
                {v.is_active && <span className="tag tag-active">当前激活</span>}
                <span className="muted">{v.created_at ? String(v.created_at).slice(0, 19) : ''}</span>
              </div>
              <div className="row-actions">
                <button onClick={() => setContent(v.content)}>查看</button>
                {!v.is_active && <button onClick={() => activate(v.id)}>激活此版本</button>}
              </div>
            </li>
          ))}
          {versions.length === 0 && <li className="muted empty">暂无版本。</li>}
        </ul>
      </section>

      <section className="card">
        <h2>试运行（仅解析，不写入）</h2>
        <textarea
          className="input-area"
          rows={2}
          placeholder="输入一条化名测试表达，如：小红今天买了一盒面膜。"
          value={testText}
          onChange={(e) => setTestText(e.target.value)}
        />
        <div className="row-actions" style={{ marginTop: 10 }}>
          <button onClick={runTest} disabled={testing}>
            {testing ? '解析中…' : '试运行'}
          </button>
        </div>
        {testResult && !testResult.error && (
          <div className="hint">
            识别客户：{testResult.customer_query}（{testResult.customer_match?.status}）
            · 操作 {testResult.actions?.length} 项
            · 提示词版本 v{testResult.prompt_version}
          </div>
        )}
      </section>

      <p className="footnote">
        提示词用于提高解析质量，不是安全边界。修改提示词无法改变后端操作白名单和余额规则。
      </p>
    </main>
  )
}
