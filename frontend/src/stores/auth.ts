import { create } from 'zustand'

export type Role = 'ADMIN' | 'OPERATOR' | 'ANALYST' | 'SUPERVISOR' | 'VIEWER'

interface AuthState {
  token: string | null
  username: string | null
  role: string | null
  setAuth: (token: string, username: string, role: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  username: localStorage.getItem('username'),
  role: localStorage.getItem('role'),
  setAuth: (token, username, role) => {
    localStorage.setItem('token', token)
    localStorage.setItem('username', username)
    localStorage.setItem('role', role)
    set({ token, username, role })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    set({ token: null, username: null, role: null })
  },
}))

export const canOperate = (role: string | null) => role === 'ADMIN' || role === 'OPERATOR'
export const canSupervise = (role: string | null) => role === 'ADMIN' || role === 'SUPERVISOR'
export const canAnalyze = (role: string | null) =>
  role === 'ADMIN' || role === 'ANALYST' || role === 'SUPERVISOR'
export const canWrite = (role: string | null) => role !== 'VIEWER' && role !== null

export const ROLE_LABEL: Record<string, string> = {
  ADMIN: '管理员',
  OPERATOR: '运行人员',
  ANALYST: '环保分析',
  SUPERVISOR: '监督员',
  VIEWER: '查看者',
}
