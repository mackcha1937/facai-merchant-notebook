import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { api } from '../api.js'
import ManageDetailView from '../components/v2/ManageDetailView.jsx'
import AdminKnowledge from '../pages/v2/AdminKnowledge.jsx'
import VerifyV2Stage5 from '../pages/v2/VerifyV2Stage5.jsx'

beforeEach(() => vi.restoreAllMocks())

const status = {
  migration: '0018_stage5_knowledge_rag',
  counts: { active_documents: 1 },
  capabilities: {
    proposal_confirmation_only: true, knowledge_versioning: true,
    confirmed_current_active_filter: true, local_deterministic_embedding: true,
    embedding_checksum_idempotency: true, dimension_isolation: true,
    hybrid_retrieval: true, tenant_metadata_filter: true,
    pii_injection_script_gate: true, stable_evidence_only: true,
  },
  runtime: { embedding_provider: 'facai-local', embedding_model: 'char-ngram-sha256-v1', dimension: 32 },
  owner_status: { embedding: { indexed: 1, failed: 0 } },
  test_results: { status: '通过', backend: '243 passed', frontend: '42 passed', build: '通过' },
}
const knowledge = [{
  document_id: 1, entity_type: 'product', entity_id: 2, knowledge_version: 1,
  status: 'published', active: true, source_name: '模拟店主确认资料',
  checksum: 'abcdef0123456789', index_status: 'indexed',
  embedding: { provider: 'facai-local', model: 'char-ngram-sha256-v1', dimension: 32 },
}]

describe('阶段5店主只读与验收页', () => {
  it('店主状态展示版本来源索引且没有可编辑技术参数', () => {
    render(<ManageDetailView group={{ id: 'ai_status' }} onBack={() => {}}
      knowledgeStatus={{
        knowledge_complete_count: 1,
        embedding: { status: 'local_only', indexed: 1, failed: 0 },
        rag: { status: 'available', result_limit: '3-5' }, recommendation_built: false,
      }} knowledge={knowledge} />)
    expect(screen.getByText(/1 个当前版本/)).toBeInTheDocument()
    expect(screen.getByText(/模拟店主确认资料 · indexed/)).toBeInTheDocument()
    expect(screen.getByText(/未建设（阶段6边界）/)).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /保存|开启|模型/ })).not.toBeInTheDocument()
    expect(screen.queryByText(/API Key:/)).not.toBeInTheDocument()
  })

  it('验收页明确本地无外部调用且检索只返回证据', async () => {
    vi.spyOn(api, 'getStage5Status').mockResolvedValue(status)
    vi.spyOn(api, 'getOwnerKnowledge').mockResolvedValue(knowledge)
    vi.spyOn(api, 'retrieveKnowledge').mockResolvedValue({
      status: 'ok', evidence: [{
        document_id: 1, knowledge_version: 1, source: { name: '模拟店主确认资料' },
        match: 'entity_name_or_alias', score: 0.96, snippet: '净痘修护面霜为日常护肤商品',
      }],
    })
    render(<MemoryRouter><VerifyV2Stage5 /></MemoryRouter>)
    expect(await screen.findByText(/facai-local · char-ngram-sha256-v1 · 32维/)).toBeInTheDocument()
    expect(screen.getByText('未调用 · 无网络依赖')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText(/输入产品/), { target: { value: '痘痘霜' } })
    fireEvent.click(screen.getByText('检索证据'))
    expect(await screen.findByText(/净痘修护面霜为日常护肤商品/)).toBeInTheDocument()
  })
})

describe('阶段5管理员 Proposal 流程', () => {
  it('先生成确认卡，再显式确认发布', async () => {
    vi.spyOn(api, 'getAdminKnowledge').mockResolvedValue([])
    vi.spyOn(api, 'getProducts').mockResolvedValue([{ id: 2, canonical_name: '净痘修护面霜', lifecycle_status: 'active' }])
    vi.spyOn(api, 'getServices').mockResolvedValue([])
    vi.spyOn(api, 'createAdminKnowledgeProposal').mockResolvedValue({
      proposal: { id: 9, data_version: 1, title: '确认发布知识', changes_summary: '发布产品知识' },
    })
    vi.spyOn(api, 'confirmAdminKnowledgeProposal').mockResolvedValue({ status: 'confirmed' })
    render(<MemoryRouter><AdminKnowledge /></MemoryRouter>)
    await screen.findByText('净痘修护面霜')
    fireEvent.change(screen.getByLabelText('实体'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('标题'), { target: { value: '产品说明' } })
    fireEvent.change(screen.getByLabelText('内容'), { target: { value: '日常护肤商品，不作医疗承诺。' } })
    fireEvent.click(screen.getByText('生成发布确认卡'))
    expect(await screen.findByTestId('knowledge-confirm-card')).toBeInTheDocument()
    expect(api.confirmAdminKnowledgeProposal).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('管理员确认并发布'))
    await waitFor(() => expect(api.confirmAdminKnowledgeProposal).toHaveBeenCalledWith(9, expect.objectContaining({ data_version: 1 })))
  })
})
