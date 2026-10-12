/**
 * 路由表与登录守卫。
 */
import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import GuideManagePage from './pages/GuideManagePage'

/** 需要登录的页面壳：无 token 跳转登录页 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading, fetchMe } = useAuthStore()
  const location = useLocation()
  const token = localStorage.getItem('token')

  useEffect(() => {
    if (token && !user && !loading) void fetchMe()
  }, [token, user, loading, fetchMe])

  if (!token) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/guides"
          element={
            <RequireAuth>
              <GuideManagePage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
