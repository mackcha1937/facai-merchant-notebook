import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Drawer, { DRAWER_ITEMS } from '../components/v2/Drawer.jsx'
import TopBar from '../components/v2/TopBar.jsx'
import ConfirmCard from '../components/v2/ConfirmCard.jsx'
import ReceiptCard from '../components/v2/ReceiptCard.jsx'
import ProductMatchCard from '../components/v2/ProductMatchCard.jsx'
import CustomerIndexCard from '../components/v2/CustomerIndexCard.jsx'
import { mockCustomers, mockProductMatches } from '../fixtures/mock/index.js'

const proposal = {
  id: 'p1',
  title: '确认操作',
  changes_summary: '面部清洁 1 次',
  absolute_date: '2026-08-22',
  precheck: '余额充足',
  original_expression: '阿珍今天面部清洁1次',
  quantity: 1,
}

describe('左侧抽屉只显示三个一级入口', () => {
  it('一级入口只有 对话/全部客户/管理与设置', () => {
    expect(DRAWER_ITEMS.map((i) => i.label)).toEqual(['对话', '全部客户', '管理与设置'])
  })

  it('点击遮罩关闭', () => {
    const onClose = vi.fn()
    render(<Drawer open onClose={onClose} onNavigate={() => {}} active="chat" />)
    fireEvent.click(screen.getByTestId('drawer-backdrop'))
    expect(onClose).toHaveBeenCalled()
  })

  it('菜单项点击导航', () => {
    const onNavigate = vi.fn()
    render(<Drawer open onClose={() => {}} onNavigate={onNavigate} active="chat" />)
    fireEvent.click(screen.getByText('全部客户'))
    expect(onNavigate).toHaveBeenCalledWith('customer_index')
  })
})

describe('今日事项顶部数字与红点', () => {
  it('unread>0 显示红点与“新”无障碍文本', () => {
    render(<TopBar onMenu={() => {}} onToday={() => {}} unresolvedCount={4} unreadCount={1} />)
    expect(screen.getByText('今日事项 4')).toBeInTheDocument()
    expect(screen.getByLabelText(/有未查看新事项/)).toBeInTheDocument()
  })

  it('unread=0 不显示“新”', () => {
    render(<TopBar onMenu={() => {}} onToday={() => {}} unresolvedCount={3} unreadCount={0} />)
    expect(screen.getByText('今日事项 3')).toBeInTheDocument()
    expect(screen.queryByLabelText(/有未查看新事项/)).not.toBeInTheDocument()
  })
})

describe('ConfirmCard', () => {
  it('展示变化摘要/绝对日期/预检查/原始表达，主按钮确认', () => {
    render(<ConfirmCard proposal={proposal} onConfirm={() => {}} onCancel={() => {}} />)
    expect(screen.getByText('确认操作')).toBeInTheDocument()
    expect(screen.getByText('面部清洁 1 次')).toBeInTheDocument()
    expect(screen.getByText('确认')).toBeInTheDocument()
  })

  it('点击确认后切换为 Mock ReceiptCard 并标记未写入', () => {
    render(<ConfirmCard proposal={proposal} onConfirm={() => {}} onCancel={() => {}} />)
    fireEvent.click(screen.getByText('确认'))
    expect(screen.getByText('阶段2演示数据，未写入真实账本')).toBeInTheDocument()
  })

  it('点击取消后显示已取消回执', () => {
    render(<ConfirmCard proposal={proposal} onConfirm={() => {}} onCancel={() => {}} />)
    fireEvent.click(screen.getByText('取消'))
    expect(screen.getAllByText('已取消').length).toBeGreaterThan(0)
  })
})

describe('ReceiptCard 状态', () => {
  it('失败状态显示重试', () => {
    const onRetry = vi.fn()
    render(<ReceiptCard status="failure" title="失败" detail="网络错误" onRetry={onRetry} />)
    expect(screen.getAllByText('失败').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByText('重试'))
    expect(onRetry).toHaveBeenCalled()
  })

  it('成功卡自动压缩并可展开', () => {
    render(<ReceiptCard status="success" title="成功" detail="未写入" />)
    expect(screen.getAllByText('成功').length).toBeGreaterThan(0)
    expect(screen.getByText('展开')).toBeInTheDocument()
  })
})

describe('ProductMatchCard 状态', () => {
  it('ambiguous 最多显示 3 个候选', () => {
    render(<ProductMatchCard match={mockProductMatches.ambiguous} onChoose={() => {}} onAddNew={() => {}} />)
    expect(screen.getAllByTestId('product-match-card')).toHaveLength(1)
    expect(screen.getByText('请问是这个吗？')).toBeInTheDocument()
    const candidates = screen.getAllByRole('button').filter((b) => b.textContent.includes('舒缓保湿'))
    expect(candidates.length).toBeLessThanOrEqual(3)
  })

  it('not_found 显示识别信息并询问是否新增', () => {
    render(<ProductMatchCard match={mockProductMatches.not_found} onAddNew={() => {}} />)
    expect(screen.getByText(/是否作为新产品新增/)).toBeInTheDocument()
    expect(screen.getByText('新增（演示）')).toBeInTheDocument()
  })
})

describe('CustomerIndexCard 搜索/筛选', () => {
  it('搜索别名过滤客户', () => {
    render(<CustomerIndexCard customers={mockCustomers} onOpenCustomer={() => {}} onBack={() => {}} />)
    fireEvent.change(screen.getByPlaceholderText('搜索客户或别名'), { target: { value: '珍姐' } })
    expect(screen.getByText(/阿珍/)).toBeInTheDocument()
    expect(screen.queryByText(/小美/)).not.toBeInTheDocument()
  })

  it('筛选待跟进', () => {
    render(<CustomerIndexCard customers={mockCustomers} onOpenCustomer={() => {}} onBack={() => {}} />)
    fireEvent.click(screen.getByText('待跟进'))
    expect(screen.getByText(/阿珍/)).toBeInTheDocument()
    expect(screen.queryByText(/小美/)).not.toBeInTheDocument()
  })
})
