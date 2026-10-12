/**
 * 路由表与登录守卫。
 * （页面心跳在 main.tsx 模块级实现，不随 React 树卸载而停止）
 */
import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import GuideManagePage from './pages/GuideManagePage'
import TaskCreatePage from './pages/TaskCreatePage'
import TaskDetailPage from './pages/TaskDetailPage'
import AnnotatePage from './pages/AnnotatePage'
import AdjudicatePage from './pages/AdjudicatePage'
import ComparePage from './pages/ComparePage'
import ExportCenterPage from './pages/ExportCenterPage'

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
        <Route
          path="/tasks/new"
          element={
            <RequireAuth>
              <TaskCreatePage />
            </RequireAuth>
          }
        />
        <Route
          path="/tasks/:id"
          element={
            <RequireAuth>
              <TaskDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/annotate/:documentId"
          element={
            <RequireAuth>
              <AnnotatePage />
            </RequireAuth>
          }
        />
        <Route
          path="/adjudicate/:documentId"
          element={
            <RequireAuth>
              <AdjudicatePage />
            </RequireAuth>
          }
        />
        <Route
          path="/compare/:documentId"
          element={
            <RequireAuth>
              <ComparePage />
            </RequireAuth>
          }
        />
        <Route
          path="/exports/:taskId"
          element={
            <RequireAuth>
              <ExportCenterPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
