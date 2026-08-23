import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
// 样式：旧版样式保留 + v1.0 设计系统
import './index.css'
import './styles/tokens.css'
import './styles/global.css'
import './styles/stage2.css'
// v1.0 页面
import ChatHome from './pages/v1/ChatHome.jsx'
import VerifyStage0 from './pages/v1/VerifyStage0.jsx'
import VerifyStage1 from './pages/v1/VerifyStage1.jsx'
import VerifyStage2 from './pages/v1/VerifyStage2.jsx'
import VerifyStage3 from './pages/v1/VerifyStage3.jsx'
import VerifyStage4 from './pages/v1/VerifyStage4.jsx'
import VerifyV2Stage0 from './pages/v2/VerifyV2Stage0.jsx'
import VerifyV2Stage1 from './pages/v2/VerifyV2Stage1.jsx'
import VerifyV2Stage2 from './pages/v2/VerifyV2Stage2.jsx'
import VerifyV2Stage3 from './pages/v2/VerifyV2Stage3.jsx'
import VerifyV2Stage4 from './pages/v2/VerifyV2Stage4.jsx'
import VerifyV2Stage5 from './pages/v2/VerifyV2Stage5.jsx'
import VerifyV2Stage6 from './pages/v2/VerifyV2Stage6.jsx'
import VerifyV2Stage7 from './pages/v2/VerifyV2Stage7.jsx'
import AdminKnowledge from './pages/v2/AdminKnowledge.jsx'
import AdminEvaluations from './pages/v2/AdminEvaluations.jsx'
import AppShell from './pages/v2/AppShell.jsx'
import CustomerSheet from './pages/v1/CustomerSheet.jsx'
import Settings from './pages/v1/Settings.jsx'
import PromptSettings from './pages/v1/PromptSettings.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatHome />} />
        <Route path="/customers" element={<CustomerSheet />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/verify/stage-0" element={<VerifyStage0 />} />
        <Route path="/verify/stage-1" element={<VerifyStage1 />} />
        <Route path="/verify/stage-2" element={<VerifyStage2 />} />
        <Route path="/verify/stage-3" element={<VerifyStage3 />} />
        <Route path="/verify/stage-4" element={<VerifyStage4 />} />
        <Route path="/verify/v2-stage-0" element={<VerifyV2Stage0 />} />
        <Route path="/verify/v2-stage-1" element={<VerifyV2Stage1 />} />
        <Route path="/verify/v2-stage-2" element={<VerifyV2Stage2 />} />
        <Route path="/verify/v2-stage-3" element={<VerifyV2Stage3 />} />
        <Route path="/verify/v2-stage-4" element={<VerifyV2Stage4 />} />
        <Route path="/verify/v2-stage-5" element={<VerifyV2Stage5 />} />
        <Route path="/verify/v2-stage-6" element={<VerifyV2Stage6 />} />
        <Route path="/verify/v2-stage-7" element={<VerifyV2Stage7 />} />
        <Route path="/admin/knowledge" element={<AdminKnowledge />} />
        <Route path="/admin/evaluations" element={<AdminEvaluations />} />
        <Route path="/app/chat" element={<AppShell initialView="chat" />} />
        <Route path="/app/customers" element={<AppShell initialView="customer_index" />} />
        <Route path="/app/manage" element={<AppShell initialView="management" />} />
        <Route path="/settings/prompt" element={<PromptSettings />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
