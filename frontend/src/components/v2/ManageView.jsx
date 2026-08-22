// 管理与设置（店主端）：产品与服务 / 数据管理 / 账号与安全 / AI运行状态（只读）。
// 每组最多三层；每个详情都有返回；从哪里进入，完成后回到哪里。
import { mockManageGroups } from '../../fixtures/mock/index.js'

export default function ManageView({ onBack, onOpenGroup }) {
  return (
    <div className="v2-block v2-manage" data-testid="manage-view">
      <div className="v2-block-head">
        <div>
          <div className="v2-block-kicker">管理与设置</div>
          <div className="v2-muted">低频入口，按分组进入，逐层返回</div>
        </div>
        <button className="v2-link" onClick={onBack}>返回对话</button>
      </div>
      <div className="v2-index-list">
        {mockManageGroups.map((g) => (
          <button key={g.id} className="v2-candidate" onClick={() => onOpenGroup?.(g)}>
            <span className="v2-candidate-main">
              <strong>{g.label}</strong>
              <span>{g.id === 'ai_status' ? '只读，不含 API Key / 提示词全文 / 阈值权重' : '演示分组'}</span>
            </span>
            <span className="v2-chevron">›</span>
          </button>
        ))}
      </div>
    </div>
  )
}
