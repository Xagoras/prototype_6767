/**
 * 登录态：token 存 localStorage，用户信息存内存。
 */
import { create } from 'zustand'
import { authApi } from '../api/client'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, displayName: string) => Promise<void>
  logout: () => void
  fetchMe: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,

  login: async (username, password) => {
    const res = await authApi.login(username, password)
    localStorage.setItem('token', res.data.token)
    const me = await authApi.me()
    set({ user: me.data })
  },

  register: async (username, password, displayName) => {
    const res = await authApi.register(username, password, displayName)
    localStorage.setItem('token', res.data.token)
    const me = await authApi.me()
    set({ user: me.data })
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null })
  },

  fetchMe: async () => {
    set({ loading: true })
    try {
      const me = await authApi.me()
      set({ user: me.data })
    } catch {
      set({ user: null })
    } finally {
      set({ loading: false })
    }
  },
}))
