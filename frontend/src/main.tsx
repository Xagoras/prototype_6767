import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// 页面心跳（模块级，不依赖 React 生命周期）：
// 一键启动脚本据此检测浏览器是否已关闭，网页关闭后自动停止前后端服务。
// 即使页面 JS 出错导致 React 树卸载，心跳也会持续，不会误触发服务停止。
const beat = () => { fetch('/api/heartbeat').catch(() => { /* 服务未就绪时忽略 */ }) }
beat()
setInterval(beat, 3000)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
