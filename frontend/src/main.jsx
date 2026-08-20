import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
// 样式：旧版样式保留 + v1.0 设计系统
import './index.css'
import './styles/tokens.css'
import './styles/global.css'
// v1.0 页面
import ChatHome from './pages/v1/ChatHome.jsx'
import VerifyStage0 from './pages/v1/VerifyStage0.jsx'
import Placeholder from './pages/v1/Placeholder.jsx'
// 旧验证页（保留，供对照）
import VerifyStage1 from './pages/VerifyStage1.jsx'
import VerifyStage2 from './pages/VerifyStage2.jsx'
import VerifyStage3 from './pages/VerifyStage3.jsx'
import VerifyStage4 from './pages/VerifyStage4.jsx'
import SettingsPrompt from './pages/SettingsPrompt.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatHome />} />
        <Route path="/customers" element={<Placeholder title="客户账本（阶段1实现）" />} />
        <Route path="/settings" element={<Placeholder title="设置（阶段1/2实现）" />} />
        <Route path="/verify/stage-0" element={<VerifyStage0 />} />
        <Route path="/verify/stage-1" element={<VerifyStage1 />} />
        <Route path="/verify/stage-2" element={<VerifyStage2 />} />
        <Route path="/verify/stage-3" element={<VerifyStage3 />} />
        <Route path="/verify/stage-4" element={<VerifyStage4 />} />
        <Route path="/settings/prompt" element={<SettingsPrompt />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
