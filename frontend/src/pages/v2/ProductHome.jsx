import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../../components/v2/Icons.jsx'
import beautyEditorialHero from '../../assets/beauty-dock-hero-v3.jpg'

const features = [
  {
    icon: 'chat',
    title: '忙的时候，说一句就记好',
    description: '做完护理不用停下来填表。说清顾客、项目和金额，发财整理好以后由你确认。',
  },
  {
    icon: 'customers',
    title: '每位顾客，都有完整档案',
    description: '称呼、偏好、护理项目、购买产品和历史消费集中保存，下次到店不用重新问一遍。',
  },
  {
    icon: 'calendar',
    title: '该跟进谁，今天就知道',
    description: '把久未到店、疗程进度和待确认记录集中到今日事项，减少因为忙碌错过的复购机会。',
  },
  {
    icon: 'microphone',
    title: '套餐余次，随时查得清',
    description: '顾客还剩几次、最近做了什么、套餐是否有效，打开档案就能看到，不再来回翻聊天记录。',
  },
  {
    icon: 'sparkles',
    title: '复购建议，不靠凭感觉',
    description: '结合顾客近期消费和已有项目给出跟进提醒，理由一起展示，店主自己决定要不要联系。',
  },
  {
    icon: 'shield',
    title: '账本变更，店主最后确认',
    description: '扣套餐、记金额和修改资料都会先展示变化，确认后才写入，忙中也不容易记错。',
  },
]

const ownerBenefits = [
  { number: '少翻', title: '聊天记录', detail: '顾客资料集中保存' },
  { number: '少算', title: '套餐余次', detail: '每次服务自动留痕' },
  { number: '少漏', title: '复购跟进', detail: '今日事项集中提醒' },
]

const previewCustomers = [
  { name: '王姐', detail: '面部护理 · 还有 3 次', tone: 'lilac' },
  { name: '小蓝', detail: '最近消费 8月20日', tone: 'green' },
  { name: '红姐', detail: '今天适合跟进', tone: 'amber' },
]

export default function ProductHome() {
  const [activeSection, setActiveSection] = useState('top')

  useEffect(() => {
    const sectionIds = ['benefits', 'features', 'workflow']
    const updateActiveSection = () => {
      if (window.scrollY < 80) {
        setActiveSection('top')
        return
      }

      const marker = window.scrollY + 150
      let nextSection = 'top'
      sectionIds.forEach((sectionId) => {
        const section = document.getElementById(sectionId)
        if (section && section.offsetTop <= marker) nextSection = sectionId
      })
      setActiveSection(nextSection)
    }

    updateActiveSection()
    window.addEventListener('scroll', updateActiveSection, { passive: true })
    return () => window.removeEventListener('scroll', updateActiveSection)
  }, [])

  return (
    <main className="product-home" id="top">
      <div className="product-home-glow product-home-glow-one" aria-hidden="true" />
      <div className="product-home-glow product-home-glow-two" aria-hidden="true" />

      <header className="product-home-header">
        <Link className="product-home-brand" to="/" aria-label="发财首页">
          <span className="product-home-logo">发</span>
          <span className="product-home-brand-copy">
            <strong>发财</strong>
            <small>商家智能记事本</small>
          </span>
        </Link>
        <nav className="product-home-nav" aria-label="首页导航">
          <a className={activeSection === 'top' ? 'active' : undefined} href="#top" aria-label="首页" aria-current={activeSection === 'top' ? 'page' : undefined} onClick={() => setActiveSection('top')}>
            <span className="nav-label-full" aria-hidden="true">首页</span>
            <span className="nav-label-short" aria-hidden="true">首页</span>
          </a>
          <a className={activeSection === 'benefits' ? 'active' : undefined} href="#benefits" aria-label="店主价值" aria-current={activeSection === 'benefits' ? 'page' : undefined} onClick={() => setActiveSection('benefits')}>
            <span className="nav-label-full" aria-hidden="true">店主价值</span>
            <span className="nav-label-short" aria-hidden="true">价值</span>
          </a>
          <a className={activeSection === 'features' ? 'active' : undefined} href="#features" aria-label="核心功能" aria-current={activeSection === 'features' ? 'page' : undefined} onClick={() => setActiveSection('features')}>
            <span className="nav-label-full" aria-hidden="true">核心功能</span>
            <span className="nav-label-short" aria-hidden="true">功能</span>
          </a>
          <a className={activeSection === 'workflow' ? 'active' : undefined} href="#workflow" aria-label="使用方式" aria-current={activeSection === 'workflow' ? 'page' : undefined} onClick={() => setActiveSection('workflow')}>
            <span className="nav-label-full" aria-hidden="true">使用方式</span>
            <span className="nav-label-short" aria-hidden="true">使用</span>
          </a>
        </nav>
      </header>

      <section className="product-home-hero" aria-labelledby="product-home-title">
        <div className="product-home-editorial">
          <div className="product-home-editorial-visual">
            <img
              src={beautyEditorialHero}
              alt="美容店顾客护理与肌肤管理氛围"
              fetchPriority="high"
            />
            <div className="product-home-editorial-caption">
              <strong>把每次用心服务，<br />变成顾客愿意再来的理由。</strong>
            </div>
          </div>

          <div className="product-home-hero-copy">
            <span className="product-home-hero-kicker"><Icon name="sparkles" size={15} />专为美容店店主设计</span>
            <h1 id="product-home-title" aria-label="懂顾客，才有每一次再来。">
              <span>懂顾客，</span>
              <span>才有每一次再来。</span>
            </h1>
            <p className="product-home-hero-description">
              顾客偏好、护理记录、套餐余次和复购跟进，一句话记好；
              下次到店前，一眼找回所有细节。
            </p>
            <div className="product-home-actions">
              <Link className="product-home-primary" to="/app/chat">
                开始管理我的顾客
                <Icon name="arrowRight" size={18} />
              </Link>
              <Link className="product-home-secondary" to="/app/customers">
                看看客户档案
              </Link>
            </div>
            <ul className="product-home-trust" aria-label="产品特点">
              <li><Icon name="check" size={15} /> 套餐余次清楚</li>
              <li><Icon name="check" size={15} /> 顾客偏好不遗漏</li>
              <li><Icon name="check" size={15} /> 到店跟进有提醒</li>
            </ul>
          </div>
        </div>

        <div className="product-home-preview-wrap" id="workspace-preview" aria-label="发财工作台界面预览">
          <div className="product-home-preview-shadow" aria-hidden="true" />
          <div className="product-home-preview">
            <aside className="product-preview-nav">
              <div className="product-preview-brand"><span>发</span><strong>发财</strong></div>
              <div className="product-preview-nav-item active"><Icon name="chat" size={18} />对话</div>
              <div className="product-preview-nav-item"><Icon name="customers" size={18} />全部客户</div>
              <div className="product-preview-nav-item"><Icon name="settings" size={18} />管理与设置</div>
              <div className="product-preview-account">
                <span>店</span>
                <div><strong>我的店铺</strong><small>经营工作台</small></div>
              </div>
            </aside>

            <div className="product-preview-chat">
              <div className="product-preview-heading">
                <div><strong>经营对话</strong><small>记账、查客户、做跟进，都可以直接告诉我</small></div>
                <span>店主工作台</span>
              </div>
              <div className="product-preview-conversation">
                <div className="product-preview-day">今天</div>
                <div className="product-preview-bubble owner">王姐今天做了一次面部护理，用套餐扣 1 次</div>
                <div className="product-preview-confirm">
                  <div className="product-preview-confirm-head">
                    <span><Icon name="check" size={15} /></span>
                    <strong>请确认这笔记录</strong>
                  </div>
                  <dl>
                    <div><dt>客户</dt><dd>王姐</dd></div>
                    <div><dt>项目</dt><dd>面部护理</dd></div>
                    <div><dt>变更</dt><dd>套餐剩余 4 → 3 次</dd></div>
                  </dl>
                  <div className="product-preview-confirm-actions">
                    <span>修改</span><strong>确认记入</strong>
                  </div>
                </div>
              </div>
              <div className="product-preview-input">
                <span>输入消息，或使用语音</span>
                <i><Icon name="microphone" size={17} /></i>
                <b><Icon name="send" size={17} /></b>
              </div>
            </div>

            <aside className="product-preview-customers">
              <div className="product-preview-customers-head">
                <div><small>客户档案</small><strong>4 位客户</strong></div>
                <span><Icon name="search" size={16} /></span>
              </div>
              {previewCustomers.map((customer) => (
                <div className="product-preview-customer" key={customer.name}>
                  <span className={customer.tone}>{customer.name.slice(0, 1)}</span>
                  <div><strong>{customer.name}</strong><small>{customer.detail}</small></div>
                  <Icon name="chevronRight" size={16} />
                </div>
              ))}
              <div className="product-preview-today">
                <span><Icon name="calendar" size={17} /></span>
                <div><strong>今日事项</strong><small>2 项待处理</small></div>
                <b>2</b>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <section className="product-home-benefits" id="benefits" aria-label="美容店店主使用收益">
        <div className="product-home-benefits-intro">
          <span>店主每天都能感受到的变化</span>
          <strong>不是多一套复杂系统，是少操几份心。</strong>
        </div>
        <div className="product-home-benefit-list">
          {ownerBenefits.map((benefit) => (
            <div className="product-home-benefit" key={benefit.title}>
              <b>{benefit.number}</b>
              <div><strong>{benefit.title}</strong><small>{benefit.detail}</small></div>
            </div>
          ))}
        </div>
      </section>

      <section className="product-home-features" id="features" aria-labelledby="feature-title">
        <div className="product-home-section-heading">
          <span>围绕美容店的一天</span>
          <h2 id="feature-title">从顾客进店，到下一次再来</h2>
          <p>不堆复杂功能，只把店主真正需要记住、查清和及时处理的事情做好。</p>
        </div>
        <div className="product-home-feature-grid">
          {features.map((feature, index) => (
            <article className="product-home-feature" key={feature.title}>
              <div className={`product-home-feature-icon tone-${(index % 3) + 1}`}>
                <Icon name={feature.icon} size={23} />
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="product-home-workflow" id="workflow" aria-labelledby="workflow-title">
        <div className="product-home-workflow-copy">
          <span className="product-home-eyebrow">店主怎么用</span>
          <h2 id="workflow-title">服务结束说一句，客户账本就跟着更新</h2>
          <p>不用培训员工学习复杂表格。像平时交代事情一样说清楚，再看一眼、确认一次。</p>
          <ol>
            <li><b>01</b><div><strong>说出顾客和本次服务</strong><small>文字或语音都可以，忙完顺手记一句。</small></div></li>
            <li><b>02</b><div><strong>核对套餐与实收变化</strong><small>顾客、项目、余次和金额集中展示。</small></div></li>
            <li><b>03</b><div><strong>确认后归入顾客档案</strong><small>下次到店前，过往情况一眼就能回想起来。</small></div></li>
          </ol>
        </div>
        <div className="product-home-workflow-card">
          <div className="product-home-workflow-orbit orbit-one" aria-hidden="true" />
          <div className="product-home-workflow-orbit orbit-two" aria-hidden="true" />
          <div className="product-home-workflow-message owner">“小蓝今天做了肩颈护理，又续了 10 次，实收 1680 元”</div>
          <div className="product-home-workflow-message assistant">
            <div className="assistant-mark"><Icon name="sparkles" size={18} /></div>
            <div><strong>已为你整理</strong><small>客户：小蓝 · 肩颈护理 10 次 · 实收 ¥1,680</small></div>
          </div>
          <div className="product-home-workflow-result"><Icon name="check" size={18} /><span>确认后写入小蓝的客户档案</span></div>
        </div>
      </section>

      <div className="product-home-back-top-wrap">
        <a className="product-home-back-top" href="#top">
          <span>返回顶部</span>
          <Icon name="back" size={17} />
        </a>
      </div>

      <footer className="product-home-footer">
        <div className="product-home-brand">
          <span className="product-home-logo">发</span>
          <span className="product-home-brand-copy"><strong>发财</strong><small>商家智能记事本</small></span>
        </div>
        <p>为认真经营每一位顾客的美容店店主而做。</p>
        <span>发财 · 商家智能记事本</span>
      </footer>
    </main>
  )
}
