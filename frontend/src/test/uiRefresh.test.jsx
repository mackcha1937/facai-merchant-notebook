import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { api } from '../api.js'
import ChatComposer from '../components/v2/ChatComposer.jsx'
import Drawer from '../components/v2/Drawer.jsx'
import LeftNav from '../components/v2/LeftNav.jsx'
import TopBar from '../components/v2/TopBar.jsx'
import WorkspaceFrame from '../components/v2/WorkspaceFrame.jsx'
import AppShell from '../pages/v2/AppShell.jsx'
import ProductHome from '../pages/v2/ProductHome.jsx'

let recognition

class FakeSpeechRecognition {
  start() {
    recognition = this
    this.onstart?.()
  }

  stop() {
    this.onend?.()
  }

  abort() {}
}

function ComposerHarness() {
  const [value, setValue] = useState('')
  return <ChatComposer input={value} onInputChange={setValue} onSend={() => {}} sending={false} />
}

function mockAppShellBase() {
  vi.spyOn(api, 'getStage6Status').mockResolvedValue({ capabilities: {} })
  vi.spyOn(api, 'getTodayRecommendations').mockResolvedValue({ items: [] })
  vi.spyOn(api, 'getProducts').mockResolvedValue([])
  vi.spyOn(api, 'getOwnerKnowledgeStatus').mockResolvedValue({})
  vi.spyOn(api, 'getOwnerKnowledge').mockResolvedValue([])
  vi.spyOn(api, 'getChatHistory').mockResolvedValue({ messages: [], next_cursor: null, has_more: false })
  vi.spyOn(api, 'getPendingActions').mockResolvedValue({ items: [] })
}

beforeEach(() => {
  recognition = null
  window.localStorage.clear()
  window.sessionStorage.clear()
  vi.restoreAllMocks()
  Object.defineProperty(window, 'SpeechRecognition', { configurable: true, value: FakeSpeechRecognition })
})

afterEach(() => {
  delete window.SpeechRecognition
  delete window.webkitSpeechRecognition
  vi.restoreAllMocks()
})

describe('真实语音输入交互', () => {
  it('麦克风位于输入框右侧，并把中文识别结果写回输入框', () => {
    const { container } = render(<ComposerHarness />)
    const composerChildren = [...container.querySelector('.v2-composer').children]
    expect(composerChildren.map((node) => node.tagName)).toEqual(['INPUT', 'BUTTON', 'BUTTON'])

    fireEvent.click(screen.getByLabelText('语音输入'))
    expect(screen.getByLabelText('停止语音输入')).toBeInTheDocument()
    act(() => {
      recognition.onresult({
        resultIndex: 0,
        results: [{ 0: { transcript: '王姐今天做了一次护理' }, isFinal: true }],
      })
    })
    fireEvent.click(screen.getByLabelText('停止语音输入'))
    expect(screen.getByDisplayValue('王姐今天做了一次护理')).toBeInTheDocument()
    expect(screen.getByText('已转成文字，可修改后发送')).toBeInTheDocument()
  })

  it('浏览器不支持时给出明确提示', () => {
    delete window.SpeechRecognition
    render(<ComposerHarness />)
    fireEvent.click(screen.getByLabelText('语音输入'))
    expect(screen.getByText(/当前浏览器不支持语音识别/)).toBeInTheDocument()
  })

  it('麦克风权限长期无响应时自动结束等待', () => {
    vi.useFakeTimers()
    class HangingSpeechRecognition {
      start() { recognition = this }
      abort() {}
    }
    Object.defineProperty(window, 'SpeechRecognition', { configurable: true, value: HangingSpeechRecognition })
    render(<ComposerHarness />)
    fireEvent.click(screen.getByLabelText('语音输入'))
    expect(screen.getByText('正在连接麦克风…')).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(10000))
    expect(screen.getByText(/麦克风连接超时/)).toBeInTheDocument()
    vi.useRealTimers()
  })
})

describe('工作区导航', () => {
  it('桌面侧栏、顶部栏和抽屉都能返回产品首页', () => {
    const desktop = render(<LeftNav active="chat" onNavigate={() => {}} />)
    expect(screen.getByRole('link', { name: '发财产品首页' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: '返回产品首页' })).toHaveAttribute('href', '/')
    desktop.unmount()

    const topbar = render(<TopBar onMenu={() => {}} onToday={() => {}} />)
    expect(screen.getByRole('link', { name: '返回产品首页' })).toHaveAttribute('href', '/')
    topbar.unmount()

    render(<Drawer open active="chat" onClose={() => {}} onNavigate={() => {}} />)
    expect(screen.getByRole('link', { name: '发财产品首页' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: '返回产品首页' })).toHaveAttribute('href', '/')
  })

  it('统一提供左侧返回和右侧关闭', () => {
    const onBack = vi.fn()
    const onClose = vi.fn()
    render(<WorkspaceFrame title="全部客户" onBack={onBack} onClose={onClose}><div>内容</div></WorkspaceFrame>)
    fireEvent.click(screen.getByLabelText('返回上一步'))
    fireEvent.click(screen.getByLabelText('关闭工作区'))
    expect(onBack).toHaveBeenCalledTimes(1)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('客户档案失败可重试，成功后显示详情', async () => {
    mockAppShellBase()
    vi.spyOn(api, 'getCustomers').mockResolvedValue([{
      id: 1, display_name: '小红', aliases: ['红姐'], last_consumed_at: null, service_type_count: 1,
    }])
    vi.spyOn(api, 'getAuthoritativeCustomerRecord')
      .mockRejectedValueOnce(new Error('临时网络错误'))
      .mockResolvedValue({
        id: 1, display_name: '小红', aliases: ['红姐'], authoritative: true, data_version: 12,
        service_type_count: 1, active_package_count: 1, services: [], recent_entries: [],
      })

    render(<AppShell initialView="customer_index" />)
    fireEvent.click(await screen.findByRole('button', { name: '查看 小红 的客户详情' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('临时网络错误')
    fireEvent.click(screen.getByText('重新加载'))
    expect(await screen.findByText('权威 #12')).toBeInTheDocument()
    expect(api.getAuthoritativeCustomerRecord).toHaveBeenCalledTimes(2)

    fireEvent.click(screen.getByLabelText('关闭工作区'))
    await waitFor(() => expect(screen.queryByTestId('right-workspace')).not.toBeInTheDocument())
  })
})

describe('产品首页', () => {
  it('展示美容店主价值、页面导航和唯一的首屏主入口', () => {
    const { container } = render(<MemoryRouter><ProductHome /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: '懂顾客，才有每一次再来。' })).toBeInTheDocument()
    expect(screen.queryByText(/CLIENT CARE|FOR BEAUTY SALON OWNERS/)).not.toBeInTheDocument()
    expect(container.querySelector('.product-home-editorial .product-home-hero-copy')).toBeInTheDocument()
    expect(container.querySelector('.product-home-editorial .product-home-preview')).not.toBeInTheDocument()
    expect(container.querySelector('.product-home-preview-wrap')).toBeInTheDocument()
    expect(container.querySelector('.product-home-preview-intro')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '从顾客进店，到下一次再来' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '忙的时候，说一句就记好' })).toBeInTheDocument()
    expect(screen.getByText('少算')).toBeInTheDocument()
    expect(screen.getByText('套餐余次')).toBeInTheDocument()

    expect(screen.getByRole('link', { name: '首页' })).toHaveAttribute('href', '#top')
    expect(screen.getByRole('link', { name: '店主价值' })).toHaveAttribute('href', '#benefits')
    expect(screen.getByRole('link', { name: '核心功能' })).toHaveAttribute('href', '#features')
    expect(screen.getByRole('link', { name: '使用方式' })).toHaveAttribute('href', '#workflow')
    fireEvent.click(screen.getByRole('link', { name: '核心功能' }))
    expect(screen.getByRole('link', { name: '核心功能' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /开始管理我的顾客/ })).toHaveAttribute('href', '/app/chat')
    expect(screen.getByRole('link', { name: '看看客户档案' })).toHaveAttribute('href', '/app/customers')
    expect(screen.queryByRole('link', { name: /进入工作台/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /返回顶部/ })).toHaveAttribute('href', '#top')
  })
})
