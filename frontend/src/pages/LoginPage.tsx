/**
 * 登录 / 注册页。
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { errMsg } from '../api/client'
import { useAuthStore } from '../stores/authStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, register } = useAuthStore()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') {
        await login(username, password)
      } else {
        await register(username, password, displayName)
      }
      navigate('/')
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>法律论证标注系统</h1>
        <p className="subtitle">裁判文书说理部分 · 法律论证结构标注与图示</p>

        <div className="mode-tabs">
          <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError('') }}>
            登录
          </button>
          <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); setError('') }}>
            注册
          </button>
        </div>

        {mode === 'register' && (
          <label>
            姓名 / 昵称
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="如：张三" />
          </label>
        )}
        <label>
          用户名
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required minLength={2} />
        </label>
        <label>
          密码
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={4} />
        </label>

        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>
          {busy ? '请稍候…' : mode === 'login' ? '登 录' : '注册并登录'}
        </button>
      </form>
    </div>
  )
}
