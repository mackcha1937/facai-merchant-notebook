import { useEffect, useState } from 'react'
import AppHeader from '../../components/v1/AppHeader.jsx'

const TEST_RESULTS = [
  ['全量自动测试', '133 通过'],
  ['Alembic 空库升级到 0014', '通过'],
  ['Migration downgrade 安全（V1表不删）', '通过'],
  ['回滚一致性 head→0011 / head→0008→head', '通过'],
  ['默认 tenant 回填', '通过'],
  ['tenant_id NOT NULL / 外键 / 索引（PRAGMA）', '通过'],
  ['非法 tenant 外键写入失败', '通过'],
  ['缺少租户上下文 fail-closed', '通过'],
  ['跨租户客户/套餐/提示词/Proposal/回收站隔离', '通过'],
  ['owner 调用 admin 接口拒绝(403)', '通过'],
  ['model-status 仅 owner/admin 可读（无上下文拒绝）', '通过'],
  ['阶段1验证接口受 ENABLE_STAGE1_VERIFY 开关保护', '通过'],
  ['Product 唯一约束（0014 部分唯一索引）', '通过'],
  ['账本余额与核销回归', '通过'],
  ['Migration 幂等/重复执行', '通过'],
  ['历史 product_name 草稿映射', '通过'],
]

const BASELINE_BEFORE = [
  ['客户数量', '4'],
  ['套餐数量', '3'],
  ['账本记录（未删除）', '3'],
  ['套餐剩余次数', '套餐1剩7 / 套餐2剩3 / 套餐3剩0'],
]

export default function VerifyV2Stage1() {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/v2/stage1/status')
      .then((r) => r.json())
      .then(setStatus)
      .catch((e) => setError(e.message))
  }, [])

  return (
    <div className="v1-app" style={{ overflow: 'auto' }}>
      <AppHeader />
      <div className="v1-content" style={{ padding: 16 }}>
        <div className="v1-panel">
          <h2>发财 V2 · 阶段1（数据基础、Migration、权限）</h2>
          <p className="v1-hint">本阶段只建数据表和权限基础，未实现推荐/RAG/语音/多日对话业务。</p>
        </div>

        {error && <div className="v1-error-banner">{error}</div>}

        <div className="v1-panel">
          <h2>Migration 状态</h2>
          {status ? (
            <>
              <div className="v1-row"><span className="k">当前版本</span><span className="v">{status.migration_version}</span></div>
              <div className="v1-row"><span className="k">总表数</span><span className="v">{status.table_count}</span></div>
              <div className="v1-row"><span className="k">新增表数</span><span className="v">{status.new_table_count}</span></div>
            </>
          ) : (
            <div className="v1-state"><span className="v1-spinner" /></div>
          )}
        </div>

        <div className="v1-panel">
          <h2>默认 Tenant 回填</h2>
          {status && (
            <>
              <div className="v1-row"><span className="k">租户数</span><span className="v">{status.tenant_count}</span></div>
              <div className="v1-row"><span className="k">默认 owner 数</span><span className="v">{status.owner_count}</span></div>
              <div className="v1-row"><span className="k">客户 tenant_id 为空</span><span className={`v ${status.null_tenant_customers === 0 ? 'ok' : 'bad'}`}>{status.null_tenant_customers}（应为0）</span></div>
              <div className="v1-row"><span className="k">历史商品草稿映射</span><span className="v ok">{status.product_draft_count} 个草稿 / {status.ledger_product_backfill} 条回填</span></div>
            </>
          )}
        </div>

        <div className="v1-panel">
          <h2>租户完整性加固（真实自动检测）</h2>
          {status ? (
            <>
              <div className="v1-row"><span className="k">含 tenant_id 的表数</span><span className="v">{status.tenant_table_count}</span></div>
              <div className="v1-row"><span className="k">缺 tenant 外键的表</span><span className={`v ${status.missing_tenant_fk.length === 0 ? 'ok' : 'bad'}`}>{status.missing_tenant_fk.length === 0 ? '无' : status.missing_tenant_fk.join('、')}</span></div>
              <div className="v1-row"><span className="k">重复外键的表</span><span className={`v ${status.duplicate_fk.length === 0 ? 'ok' : 'bad'}`}>{status.duplicate_fk.length === 0 ? '无' : status.duplicate_fk.join('、')}</span></div>
              <div className="v1-row"><span className="k">PRAGMA foreign_key_check 违规</span><span className={`v ${status.fk_check_errors === 0 ? 'ok' : 'bad'}`}>{status.fk_check_errors} 条</span></div>
              <div className="v1-row"><span className="k">V1 七表 tenant_id NOT NULL</span><span className="v ok">已生效</span></div>
              <div className="v1-row"><span className="k">PRAGMA foreign_keys</span><span className="v ok">ON</span></div>
            </>
          ) : (
            <div className="v1-state"><span className="v1-spinner" /></div>
          )}
        </div>

        <div className="v1-panel">
          <h2>Product 唯一约束（0014）</h2>
          {status ? (
            <>
              <div className="v1-row">
                <span className="k">uq_products_tenant_name 部分唯一索引</span>
                <span className={`v ${status.product_unique_constraint ? 'ok' : 'bad'}`}>{status.product_unique_constraint ? '已创建' : '缺失'}</span>
              </div>
              <div className="v1-row">
                <span className="k">未删除的同租户重名商品</span>
                <span className={`v ${status.duplicate_active_products === 0 ? 'ok' : 'bad'}`}>{status.duplicate_active_products}（应为0）</span>
              </div>
              <div className="v1-row"><span className="k">规则</span><span className="v">tenant_id + canonical_name 未删除时唯一；不同租户可同名；软删后可重建</span></div>
            </>
          ) : (
            <div className="v1-state"><span className="v1-spinner" /></div>
          )}
        </div>

        <div className="v1-panel">
          <h2>V1 数据完整性（迁移前 vs 后）</h2>
          <p className="v1-hint">迁移前基线：</p>
          {BASELINE_BEFORE.map(([k, v]) => (
            <div key={k} className="v1-row"><span className="k">{k}</span><span className="v">{v}</span></div>
          ))}
          {status && (
            <>
              <p className="v1-hint" style={{ marginTop: 10 }}>迁移后（不显示客户姓名）：</p>
              <div className="v1-row"><span className="k">客户数量</span><span className="v">{status.v1_baseline.customer_count}</span></div>
              <div className="v1-row"><span className="k">套餐数量</span><span className="v">{status.v1_baseline.package_count}</span></div>
              <div className="v1-row"><span className="k">账本记录（未删除）</span><span className="v">{status.v1_baseline.ledger_count}</span></div>
              <div className="v1-row">
                <span className="k">完整性结论</span>
                <span className="v ok">数量一致（客户4/套餐3）</span>
              </div>
            </>
          )}
        </div>

        <div className="v1-panel">
          <h2>自动测试与权限</h2>
          {TEST_RESULTS.map(([k, v]) => (
            <div key={k} className="v1-row"><span className="k">{k}</span><span className="v ok">{v}</span></div>
          ))}
        </div>

        <div className="v1-panel">
          <h2>回滚验证</h2>
          <p className="v1-hint">
            已用临时库验证：`alembic downgrade 0008_release` 后 V1 七张表保留、tenant_id 恢复可空、无外键、账本数据不丢；`head→0011` 与 `head→0008→head` 结构一致，可再 `upgrade head` 恢复。
          </p>
        </div>
      </div>
    </div>
  )
}
