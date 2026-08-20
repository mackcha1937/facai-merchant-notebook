import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.jsx'
import VerifyStage0 from './pages/VerifyStage0.jsx'
import VerifyStage1 from './pages/VerifyStage1.jsx'
import VerifyStage2 from './pages/VerifyStage2.jsx'
import VerifyStage3 from './pages/VerifyStage3.jsx'
import VerifyStage4 from './pages/VerifyStage4.jsx'
import SettingsPrompt from './pages/SettingsPrompt.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
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
