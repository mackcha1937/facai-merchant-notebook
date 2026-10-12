import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
// 样式：旧版样式保留 + v1.0 设计系统
import './index.css'
import './styles/tokens.css'
import './styles/global.css'
import './styles/stage2.css'
import './styles/landing.css'
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
import VerifyV2Stage8 from './pages/v2/VerifyV2Stage8.jsx'
import AdminKnowledge from './pages/v2/AdminKnowledge.jsx'
import AdminEvaluations from './pages/v2/AdminEvaluations.jsx'
import AppShell from './pages/v2/AppShell.jsx'
import ProductHome from './pages/v2/ProductHome.jsx'
import LoginPage from './pages/v2/LoginPage.jsx'
import AuthGate from './components/v2/AuthGate.jsx'
import CustomerSheet from './pages/v1/CustomerSheet.jsx'
import Settings from './pages/v1/Settings.jsx'
import PromptSettings from './pages/v1/PromptSettings.jsx'

const protectedPage = (page) => <AuthGate>{page}</AuthGate>

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ProductHome />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/customers" element={protectedPage(<CustomerSheet />)} />
        <Route path="/settings" element={protectedPage(<Settings />)} />
        <Route path="/verify/stage-0" element={protectedPage(<VerifyStage0 />)} />
        <Route path="/verify/stage-1" element={protectedPage(<VerifyStage1 />)} />
        <Route path="/verify/stage-2" element={protectedPage(<VerifyStage2 />)} />
        <Route path="/verify/stage-3" element={protectedPage(<VerifyStage3 />)} />
        <Route path="/verify/stage-4" element={protectedPage(<VerifyStage4 />)} />
        <Route path="/verify/v2-stage-0" element={protectedPage(<VerifyV2Stage0 />)} />
        <Route path="/verify/v2-stage-1" element={protectedPage(<VerifyV2Stage1 />)} />
        <Route path="/verify/v2-stage-2" element={protectedPage(<VerifyV2Stage2 />)} />
        <Route path="/verify/v2-stage-3" element={protectedPage(<VerifyV2Stage3 />)} />
        <Route path="/verify/v2-stage-4" element={protectedPage(<VerifyV2Stage4 />)} />
        <Route path="/verify/v2-stage-5" element={protectedPage(<VerifyV2Stage5 />)} />
        <Route path="/verify/v2-stage-6" element={protectedPage(<VerifyV2Stage6 />)} />
        <Route path="/verify/v2-stage-7" element={protectedPage(<VerifyV2Stage7 />)} />
        <Route path="/verify/v2-stage-8" element={protectedPage(<VerifyV2Stage8 />)} />
        <Route path="/admin/knowledge" element={protectedPage(<AdminKnowledge />)} />
        <Route path="/admin/evaluations" element={protectedPage(<AdminEvaluations />)} />
        <Route path="/app/chat" element={protectedPage(<AppShell initialView="chat" />)} />
        <Route path="/app/customers" element={protectedPage(<AppShell initialView="customer_index" />)} />
        <Route path="/app/manage" element={protectedPage(<AppShell initialView="management" />)} />
        <Route path="/settings/prompt" element={protectedPage(<PromptSettings />)} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
