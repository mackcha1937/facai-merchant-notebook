import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.jsx'
import VerifyStage0 from './pages/VerifyStage0.jsx'
import VerifyStage1 from './pages/VerifyStage1.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/verify/stage-0" element={<VerifyStage0 />} />
        <Route path="/verify/stage-1" element={<VerifyStage1 />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
