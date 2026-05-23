export interface ApiResponse<T> { code: number; message: string; data: T }
export interface PaginatedResponse<T> {
  items: T[]; total: number; page: number; page_size: number; total_pages: number
}

export type UnitStatus = 'RUNNING' | 'STANDBY' | 'OUTAGE' | 'DECOMMISSIONED'
export type FuelType = 'COAL' | 'GAS' | 'OIL' | 'BIOMASS'
export interface Unit {
  id: number; code: string; name: string; capacity_mw: number;
  fuel_type: FuelType; status: UnitStatus;
  commission_date?: string; notes?: string;
  point_count: number; created_at: string; updated_at: string
}

export type PointCategory = 'STACK' | 'PRE_DESULFUR' | 'POST_DESULFUR' | 'PRE_DENOX' | 'POST_DENOX'
export interface EmissionPoint {
  id: number; code: string; name: string;
  unit_id: number; unit_code?: string; unit_name?: string;
  category: PointCategory; location?: string;
  standard_id?: number; is_compliance_point: boolean;
  notes?: string; created_at: string
}

export type CemsStatus = 'ONLINE' | 'OFFLINE' | 'CALIBRATING' | 'FAULT'
export interface CemsDevice {
  id: number; code: string; name: string; point_id: number; point_code?: string;
  manufacturer?: string; model?: string; serial_no?: string;
  install_date?: string; last_calibration_at?: string; next_calibration_at?: string;
  status: CemsStatus; is_certified: boolean; certification_expiry?: string;
  notes?: string; created_at: string; updated_at: string
}

export type ReadingValidity = 'VALID' | 'INVALID' | 'CALIBRATING' | 'SUBSTITUTED'
export interface Reading {
  id: number; point_id: number; cems_id?: number; measured_at: string;
  so2?: number; nox?: number; dust?: number; co?: number;
  o2?: number; temperature?: number; humidity?: number; flow?: number; velocity?: number;
  so2_corrected?: number; nox_corrected?: number; dust_corrected?: number;
  validity: ReadingValidity; severity?: string; exceeded?: string;
  created_at: string
}

export interface RealtimeItem {
  point_id: number; point_code: string; point_name: string;
  unit_code: string; unit_name: string;
  measured_at?: string;
  so2?: number; nox?: number; dust?: number; o2?: number; flow?: number;
  validity?: string; severity?: string; exceeded: string[];
}

export type AlertSeverity = 'GENERAL' | 'SEVERE' | 'ESCALATED'
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'HANDLING' | 'RESOLVED' | 'CLOSED'
export interface EmissionAlert {
  id: number; alert_no: string; point_id: number;
  point_code?: string; unit_name?: string;
  severity: AlertSeverity; status: AlertStatus;
  indicators: string;
  peak_so2?: number; peak_nox?: number; peak_dust?: number;
  description?: string; started_at: string; ended_at?: string; duration_minutes: number;
  acknowledged_by?: string; acknowledged_at?: string;
  handled_by?: string; handle_notes?: string; handled_at?: string;
  resolution?: string; closed_by?: string; closed_at?: string;
  created_at: string
}

export type ReportType = 'DAILY' | 'MONTHLY' | 'YEARLY' | 'AD_HOC'
export type ReportStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'ARCHIVED'
export interface EmissionReport {
  id: number; report_no: string; report_type: ReportType;
  period_start: string; period_end: string;
  title: string; summary: any; notes?: string;
  status: ReportStatus;
  generated_by?: string; generated_at: string;
  submitted_by?: string; submitted_at?: string;
  approved_by?: string; approved_at?: string;
  created_at: string
}

export interface DashboardOverview {
  cems: { total: number; online: number; fault: number };
  alerts: { today: number; open: number; severe_open: number };
  compliance_30d_pct: number;
  availability_30d_pct: number;
  availability_target: number;
}

export const POINT_CATEGORY_LABEL: Record<PointCategory, string> = {
  STACK: '烟囱出口', PRE_DESULFUR: '脱硫前', POST_DESULFUR: '脱硫后',
  PRE_DENOX: '脱硝前', POST_DENOX: '脱硝后',
}

export const CEMS_STATUS_LABEL: Record<CemsStatus, string> = {
  ONLINE: '在线', OFFLINE: '离线', CALIBRATING: '校准中', FAULT: '故障',
}

export const ALERT_SEVERITY_LABEL: Record<AlertSeverity, string> = {
  GENERAL: '一般', SEVERE: '严重', ESCALATED: '升级',
}

export const ALERT_STATUS_LABEL: Record<AlertStatus, string> = {
  OPEN: '待确认', ACKNOWLEDGED: '已确认', HANDLING: '处置中',
  RESOLVED: '已解决', CLOSED: '已归档',
}

export const REPORT_TYPE_LABEL: Record<ReportType, string> = {
  DAILY: '日报', MONTHLY: '月报', YEARLY: '年报', AD_HOC: '临时',
}

export const REPORT_STATUS_LABEL: Record<ReportStatus, string> = {
  DRAFT: '草稿', SUBMITTED: '已提交', APPROVED: '已审批', ARCHIVED: '已归档',
}
