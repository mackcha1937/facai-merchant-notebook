// 管理与设置详情（第二级）。AI运行状态为只读：无输入框、开关、保存按钮、API Key。
import { useState } from 'react'
import { mockAiStatus } from '../../fixtures/mock/index.js'

const GROUP_DETAIL = {
  products_services: {
    title: '产品与服务',
    rows: [
      ['服务项目', '5 个（Mock）'],
      ['产品', '1 个（Mock）'],
      ['资料待补充', '0 个'],
    ],
  },
  data_management: {
    title: '数据管理',
    rows: [
      ['导入', '选文件 → 预览 → 确认（阶段2演示）'],
      ['导出', '选范围 → 生成 → 下载（阶段2演示）'],
      ['恢复', '查看影响 → 备份 → 恢复（阶段2演示）'],
    ],
  },
  account_security: {
    title: '账号与安全',
    rows: [
      ['店主账号', 'owner（Mock）'],
      ['登录方式', '本地开发默认身份'],
    ],
  },
  ai_status: {
    title: 'AI运行状态（只读）',
    readOnly: true,
  },
}

export default function ManageDetailView({ group, onBack, products = [], onCreateProduct, onMergeProducts }) {
  const detail = GROUP_DETAIL[group?.id] || GROUP_DETAIL.products_services
  const [draft, setDraft] = useState({ canonical_name: '', brand: '', specification: '' })
  const [merge, setMerge] = useState({ source_product_id: '', target_product_id: '' })
  const [error, setError] = useState('')

  if (group?.id === 'products_services') {
    const create = async () => {
      setError('')
      try {
        await onCreateProduct?.(draft)
        setDraft({ canonical_name: '', brand: '', specification: '' })
      } catch (failure) { setError(failure.message) }
    }
    const mergeNow = async () => {
      setError('')
      try { await onMergeProducts?.({ source_product_id: Number(merge.source_product_id), target_product_id: Number(merge.target_product_id) }) }
      catch (failure) { setError(failure.message) }
    }
    return (
      <div className="v2-block v2-manage" data-testid="manage-detail-view">
        <div className="v2-path"><button className="v2-link" onClick={onBack}>← 返回管理与设置</button></div>
        <div className="v2-record-title">产品与服务</div>
        {error && <p className="v2-inline-error">{error}</p>}
        <div className="v2-section">
          <strong>产品实体（{products.length}）</strong>
          {products.map((product) => (
            <div className="v2-kv" key={product.id}>
              <span className="k">{product.canonical_name}</span>
              <span className="v">{product.lifecycle_status} · {product.knowledge_status === 'incomplete' ? '资料待补充' : product.knowledge_status} · 购买{product.purchase_count}次</span>
            </div>
          ))}
          {products.length === 0 && <div className="v2-state">暂无产品，可先创建草稿</div>}
        </div>
        <div className="v2-edit-inline">
          <label>标准名称<input value={draft.canonical_name} onChange={(event) => setDraft((value) => ({ ...value, canonical_name: event.target.value }))} /></label>
          <label>品牌（可空）<input value={draft.brand} onChange={(event) => setDraft((value) => ({ ...value, brand: event.target.value }))} /></label>
          <label>规格（可空）<input value={draft.specification} onChange={(event) => setDraft((value) => ({ ...value, specification: event.target.value }))} /></label>
          <button className="v2-btn" disabled={!draft.canonical_name.trim()} onClick={create}>生成新增确认卡</button>
        </div>
        {products.length >= 2 && <div className="v2-edit-inline">
          <label>待合并产品<select value={merge.source_product_id} onChange={(event) => setMerge((value) => ({ ...value, source_product_id: event.target.value }))}><option value="">请选择</option>{products.filter((p) => ['draft', 'active'].includes(p.lifecycle_status)).map((p) => <option key={p.id} value={p.id}>{p.canonical_name}</option>)}</select></label>
          <label>保留产品<select value={merge.target_product_id} onChange={(event) => setMerge((value) => ({ ...value, target_product_id: event.target.value }))}><option value="">请选择</option>{products.filter((p) => ['draft', 'active'].includes(p.lifecycle_status)).map((p) => <option key={p.id} value={p.id}>{p.canonical_name}</option>)}</select></label>
          <button className="v2-btn" disabled={!merge.source_product_id || !merge.target_product_id || merge.source_product_id === merge.target_product_id} onClick={mergeNow}>生成合并确认卡</button>
        </div>}
        <p className="v2-hint">新增与合并不会在本页直接写入；将回到主对话完成一次最终确认。也可用文字或语音说“新增产品…”或“把…合并到…”。</p>
      </div>
    )
  }

  if (detail.readOnly) {
    return (
      <div className="v2-block v2-manage" data-testid="manage-detail-view">
        <div className="v2-path"><button className="v2-link" onClick={onBack}>← 返回管理与设置</button></div>
        <div className="v2-record-title">{detail.title}</div>
        <div className="v2-kv"><span className="k">对话模型</span><span className="v">{mockAiStatus.chat_model.id} · {mockAiStatus.chat_model.status}</span></div>
        <div className="v2-kv"><span className="k">Embedding</span><span className="v">{mockAiStatus.embedding.status}</span></div>
        <div className="v2-kv"><span className="k">RAG</span><span className="v">{mockAiStatus.rag.status}</span></div>
        <div className="v2-kv"><span className="k">推荐</span><span className="v">{mockAiStatus.recommendation.status}</span></div>
        <div className="v2-kv"><span className="k">最近检查</span><span className="v">{mockAiStatus.last_check_at}</span></div>
        <p className="v2-hint">本页只读，无输入框、开关、保存按钮，也不返回 API Key 或提示词全文。</p>
      </div>
    )
  }

  return (
    <div className="v2-block v2-manage" data-testid="manage-detail-view">
      <div className="v2-path"><button className="v2-link" onClick={onBack}>← 返回管理与设置</button></div>
      <div className="v2-record-title">{detail.title}</div>
      {detail.rows.map(([k, v]) => (
        <div key={k} className="v2-kv"><span className="k">{k}</span><span className="v">{v}</span></div>
      ))}
      <p className="v2-hint">（阶段2演示：进入 → 查看 → 返回来源位置）</p>
    </div>
  )
}
