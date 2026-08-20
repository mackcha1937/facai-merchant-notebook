import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './components/AppLayout.jsx'
import Home from './pages/Home.jsx'
import Customers from './pages/Customers.jsx'
import CustomerDetail from './pages/CustomerDetail.jsx'
import Record from './pages/Record.jsx'
import Services from './pages/Services.jsx'
import Trash from './pages/Trash.jsx'
import SettingsPrompt from './pages/SettingsPrompt.jsx'
import VerifyStage0 from './pages/VerifyStage0.jsx'
import VerifyStage1 from './pages/VerifyStage1.jsx'
import VerifyStage2 from './pages/VerifyStage2.jsx'
import VerifyStage3 from './pages/VerifyStage3.jsx'
import VerifyStage4 from './pages/VerifyStage4.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/customers/:id" element={<CustomerDetail />} />
          <Route path="/record" element={<Record />} />
          <Route path="/services" element={<Services />} />
          <Route path="/trash" element={<Trash />} />
          <Route path="/settings/prompt" element={<SettingsPrompt />} />
        </Route>
        <Route path="/verify/stage-0" element={<VerifyStage0 />} />
        <Route path="/verify/stage-1" element={<VerifyStage1 />} />
        <Route path="/verify/stage-2" element={<VerifyStage2 />} />
        <Route path="/verify/stage-3" element={<VerifyStage3 />} />
        <Route path="/verify/stage-4" element={<VerifyStage4 />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
