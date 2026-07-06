import { request, type ApiResponse, type RequestConfig } from './request'

export interface TrainingSessionCreateRequest {
  symbol: string
  start_date?: string
  end_date?: string
  initial_cash?: number
  total_days?: number
  market?: 'CN'
  note?: string
}

export interface TrainingActionRequest {
  side: 'buy' | 'sell'
  quantity: number
  price: number
  trade_date?: string
  reason?: string
}

export interface TrainingPosition {
  symbol: string
  quantity: number
  avg_cost: number
  market_value: number
  unrealized_pnl: number
}

export interface TrainingAdvice {
  trend_strength: string
  volume_change: string
  t_suitability: string
  risk_level: string
  chase_risk: string
  dip_buy_suitability: string
  position_range: string
  reason: string
}

export interface TrainingSessionResponse {
  session_id: string
  symbol: string
  symbol_name?: string
  market?: 'CN'
  start_date: string
  end_date: string
  current_step: number
  total_days: number
  initial_cash: number
  cash: number
  positions: TrainingPosition[]
  realized_pnl: number
  unrealized_pnl: number
  total_equity: number
  trade_count: number
  status: 'active' | 'finished' | 'paused'
  created_at: string
  updated_at: string
}

export interface TrainingSessionSummary {
  session_id: string
  symbol: string
  symbol_name?: string
  market?: 'CN'
  start_date: string
  end_date: string
  current_step: number
  total_days: number
  initial_cash: number
  cash: number
  total_equity: number
  trade_count: number
  active_return?: number | null
  buy_and_hold_return?: number | null
  excess_return?: number | null
  score?: number | null
  status: 'active' | 'finished' | 'paused'
  note?: string | null
  created_at: string
  updated_at: string
}

export interface TrainingReplayBar {
  trade_date: string
  open?: number | null
  high?: number | null
  low?: number | null
  close?: number | null
  volume?: number | null
  amount?: number | null
}

export interface TrainingReplayStep {
  trade_date: string
  bar_index: number
  visible_bars: TrainingReplayBar[]
  is_finished: boolean
  current_price?: number | null
  advice?: TrainingAdvice | null
  session?: TrainingSessionResponse | null
}

export interface TrainingReport {
  session_id: string
  symbol: string
  start_date: string
  end_date: string
  final_cash: number
  final_equity: number
  realized_pnl: number
  unrealized_pnl: number
  active_return: number
  buy_and_hold_return: number
  excess_return: number
  score: number
  trade_count: number
  max_drawdown: number
  good_trades: Array<Record<string, any>>
  bad_trades: Array<Record<string, any>>
  advice: string
}

export const trainingApi = {
  createSession(payload: TrainingSessionCreateRequest): Promise<ApiResponse<TrainingSessionResponse>> {
    return request.post('/api/training/sessions', payload)
  },

  getSession(sessionId: string, config?: RequestConfig): Promise<ApiResponse<TrainingSessionResponse>> {
    return request.get(`/api/training/sessions/${sessionId}`, config)
  },

  listSessions(config?: RequestConfig): Promise<ApiResponse<TrainingSessionSummary[]>> {
    return request.get('/api/training/sessions', config)
  },

  getStep(sessionId: string, config?: RequestConfig): Promise<ApiResponse<TrainingReplayStep>> {
    return request.get(`/api/training/sessions/${sessionId}/step`, config)
  },

  submitAction(sessionId: string, payload: TrainingActionRequest): Promise<ApiResponse<TrainingSessionResponse>> {
    return request.post(`/api/training/sessions/${sessionId}/actions`, payload)
  },

  advance(sessionId: string): Promise<ApiResponse<TrainingReplayStep>> {
    return request.post(`/api/training/sessions/${sessionId}/advance`, {})
  },

  finish(sessionId: string): Promise<ApiResponse<TrainingReport>> {
    return request.post(`/api/training/sessions/${sessionId}/finish`, {})
  },

  getReport(sessionId: string, config?: RequestConfig): Promise<ApiResponse<TrainingReport>> {
    return request.get(`/api/training/sessions/${sessionId}/report`, config)
  },
}
