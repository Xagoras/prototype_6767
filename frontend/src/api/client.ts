/**
 * axios 封装：自动附带 JWT、统一错误处理。
 * 开发环境经 vite proxy 转发到后端（见 vite.config.ts）。
 */
import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

// 请求拦截：附带 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：401 时清除登录态并跳转登录页
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

/** 提取后端错误信息（FastAPI detail 字段） */
export function errMsg(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join('；')
    return err.message
  }
  return String(err)
}

/** 同 errMsg，但兼容 responseType:'blob' 的错误响应（如导出中心下载 409）：
 *  此时 err.response.data 是 Blob，需异步读出文本再取 detail。 */
export async function errMsgFromBlob(err: unknown): Promise<string> {
  if (axios.isAxiosError(err) && err.response?.data instanceof Blob) {
    try {
      const parsed = JSON.parse(await err.response.data.text())
      const detail = parsed?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) return detail.map((d) => d.msg).join('；')
    } catch {
      /* 非 JSON blob，回落 errMsg */
    }
  }
  return errMsg(err)
}

// ---------- 认证 ----------
import type { TokenResponse, User } from '../types'

export const authApi = {
  register: (username: string, password: string, display_name: string) =>
    api.post<TokenResponse>('/auth/register', { username, password, display_name }),
  login: (username: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { username, password }),
  me: () => api.get<User>('/auth/me'),
}

export const usersApi = {
  list: () => api.get<User[]>('/users'),
}
