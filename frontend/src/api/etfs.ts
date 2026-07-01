import { ApiClient } from './request'

/** ETF 自选项 */
export interface EtfItem {
  fund_code: string       // ETF 代码（6位）
  fund_name: string       // ETF 名称
  fund_type: string       // 类型：宽基/行业/主题/跨境/策略
  added_at?: string
  tags?: string[]
  notes?: string
  alert_price_high?: number | null
  alert_price_low?: number | null
  // 实时行情（后端富集）
  current_price?: number | null
  change_percent?: number | null
  turnover_rate?: number | null  // 换手率(%)
  volume_ratio?: number | null   // 量比
}

/** 添加 ETF 请求 */
export interface AddEtfReq {
  fund_code: string
  fund_name: string
  fund_type?: string
  tags?: string[]
  notes?: string
}

/** 预置热门 ETF 条目（含实时行情 + 是否已加入） */
export interface PopularEtf {
  fund_code: string
  fund_name: string
  fund_type: string
  current_price?: number | null
  change_percent?: number | null
  is_added?: boolean
}

export const etfsApi = {
  /** 获取 ETF 自选列表（含实时行情） */
  list: () => ApiClient.get<EtfItem[]>('/api/etfs/'),

  /** 获取预置热门 ETF 清单 */
  popular: () => ApiClient.get<PopularEtf[]>('/api/etfs/popular'),

  /** 添加 ETF */
  add: (payload: AddEtfReq) => ApiClient.post('/api/etfs/', payload),

  /** 批量导入 ETF */
  batchAdd: (items: AddEtfReq[]) =>
    ApiClient.post<{ added: string[]; existed: string[]; failed: string[] }>('/api/etfs/batch', { items }),

  /** 更新 ETF（备注/标签） */
  update: (fundCode: string, payload: Partial<AddEtfReq> & { notes?: string; tags?: string[] }) =>
    ApiClient.put(`/api/etfs/${fundCode}`, payload),

  /** 移除 ETF */
  remove: (fundCode: string) => ApiClient.delete(`/api/etfs/${fundCode}`),

  /** 检查是否已收藏 */
  check: (fundCode: string) =>
    ApiClient.get<{ is_favorite: boolean }>(`/api/etfs/check/${fundCode}`),

  /** 获取所有标签 */
  tags: () => ApiClient.get<string[]>('/api/etfs/tags'),
}
