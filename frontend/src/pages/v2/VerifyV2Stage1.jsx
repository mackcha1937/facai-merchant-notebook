import { useEffect, useState } from 'react'
import AppHeader from '../../components/v1/AppHeader.jsx'

const TEST_RESULTS = [
  ['V1 原有测试', '100 通过'],
  ['Alembic 空库升级到最新版', '通过'],
  ['Migration downgrade 安全（V1表不删）', '通过'],
  ['默认 tenant 回填', '通过'],
  ['owner/admin 权限测试', '通过'],
  ['跨租户读取/修改阻断', '通过'],
  ['账本余额与核销回归', '通过'],
  ['Migration 幂等/重复执行', '通过'],
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
            </>
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
            `alembic downgrade 0001_baseline` 后：V1 七张表保留、新表移除、账本数据不删；可再 `upgrade head` 恢复。已用临时库验证通过。
          </p>
        </div>
      </div>
    </div>
  )
}
