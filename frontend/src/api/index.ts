import axios from 'axios'
import type {
  ApiResponse, PaginatedResponse,
  Unit, UnitStatus, EmissionPoint, PointCategory,
  CemsDevice, CemsStatus,
  RealtimeItem, EmissionAlert, AlertStatus, AlertSeverity,
  EmissionReport, ReportType, ReportStatus,
  DashboardOverview,
} from '../types'

const api = axios.create({ baseURL: '/api', timeout: 15000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err.response?.data || err)
  },
)

export const authApi = {
  login: (username: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return api.post<unknown, { access_token: string; token_type: string }>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  me: () => api.get<unknown, ApiResponse<{ id: number; username: string; role: string }>>('/auth/me'),
}

export const unitApi = {
  list: (params?: { page?: number; page_size?: number; status?: UnitStatus }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<Unit>>>('/units', { params }),
  create: (data: Partial<Unit>) => api.post<unknown, ApiResponse<Unit>>('/units', data),
  update: (id: number, data: Partial<Unit>) => api.put<unknown, ApiResponse<Unit>>(`/units/${id}`, data),
  listPoints: (params?: { page?: number; page_size?: number; unit_id?: number; category?: PointCategory }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<EmissionPoint>>>('/emission-points', { params }),
}

export const cemsApi = {
  list: (params?: { page?: number; page_size?: number; point_id?: number; status?: CemsStatus }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<CemsDevice>>>('/cems', { params }),
  create: (data: any) => api.post<unknown, ApiResponse<CemsDevice>>('/cems', data),
  update: (id: number, data: any) => api.put<unknown, ApiResponse<CemsDevice>>(`/cems/${id}`, data),
  calibrateStart: (id: number) => api.post<unknown, ApiResponse<null>>(`/cems/${id}/calibrate-start`),
  calibrateFinish: (id: number) => api.post<unknown, ApiResponse<null>>(`/cems/${id}/calibrate-finish`),
}

export const readingApi = {
  ingest: (readings: any[]) => api.post<unknown, ApiResponse<{ saved: number; alerts_created: number }>>('/readings/ingest', { readings }),
  latest: () => api.get<unknown, ApiResponse<any[]>>('/readings/latest'),
  hourly: (point_id: number, hours = 24) =>
    api.get<unknown, ApiResponse<any[]>>('/readings/hourly', { params: { point_id, hours } }),
  list: (params: any) => api.get<unknown, ApiResponse<PaginatedResponse<any>>>('/readings', { params }),
}

export const alertApi = {
  list: (params?: { page?: number; page_size?: number; status?: AlertStatus; severity?: AlertSeverity; point_id?: number }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<EmissionAlert>>>('/alerts', { params }),
  get: (id: number) => api.get<unknown, ApiResponse<EmissionAlert>>(`/alerts/${id}`),
  acknowledge: (id: number, notes?: string) => api.post<unknown, ApiResponse<null>>(`/alerts/${id}/acknowledge`, { notes }),
  handle: (id: number, handle_notes: string, resolution?: string) =>
    api.post<unknown, ApiResponse<null>>(`/alerts/${id}/handle`, { handle_notes, resolution }),
  resolve: (id: number, resolution: string) => api.post<unknown, ApiResponse<null>>(`/alerts/${id}/resolve`, { resolution }),
  close: (id: number) => api.post<unknown, ApiResponse<null>>(`/alerts/${id}/close`),
}

export const reportApi = {
  list: (params?: { page?: number; page_size?: number; status?: ReportStatus; report_type?: ReportType }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<EmissionReport>>>('/reports', { params }),
  generate: (data: { report_type: ReportType; period_start: string; period_end: string; title?: string; notes?: string }) =>
    api.post<unknown, ApiResponse<EmissionReport>>('/reports/generate', data),
  get: (id: number) => api.get<unknown, ApiResponse<EmissionReport>>(`/reports/${id}`),
  submit: (id: number) => api.post<unknown, ApiResponse<null>>(`/reports/${id}/submit`),
  approve: (id: number) => api.post<unknown, ApiResponse<null>>(`/reports/${id}/approve`),
}

export const dashboardApi = {
  overview: () => api.get<unknown, ApiResponse<DashboardOverview>>('/dashboard/overview'),
  realtime: () => api.get<unknown, ApiResponse<{ limits: { so2: number; nox: number; dust: number }; items: RealtimeItem[] }>>('/dashboard/realtime'),
  trend24h: (point_id: number) => api.get<unknown, ApiResponse<Array<{ hour: string; so2: number; nox: number; dust: number }>>>('/dashboard/trend-24h', { params: { point_id } }),
  alertDistribution: (days = 30) => api.get<unknown, ApiResponse<{ by_severity: Array<{ name: string; value: number }>; by_status: Array<{ name: string; value: number }> }>>('/dashboard/alert-distribution', { params: { days } }),
  pointCompliance: (days = 30) =>
    api.get<unknown, ApiResponse<Array<{ point_id: number; point_code: string; compliance_pct: number; valid_minutes: number; exceed_minutes: number }>>>('/dashboard/point-compliance', { params: { days } }),
}

export default api
