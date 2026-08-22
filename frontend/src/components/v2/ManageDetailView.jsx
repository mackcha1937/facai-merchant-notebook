// 管理与设置详情（第二级）。AI运行状态为只读：无输入框、开关、保存按钮、API Key。
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

export default function ManageDetailView({ group, onBack }) {
  const detail = GROUP_DETAIL[group?.id] || GROUP_DETAIL.products_services

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
