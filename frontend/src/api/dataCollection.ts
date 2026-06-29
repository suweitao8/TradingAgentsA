import { ApiClient } from './request'

/** 股票数据采集结果 - 单只股票 */
export interface StockDataItem {
  code: string
  name: string
  market_board: string
  price: number | null
  change_percent: number | null
  speed: number | null
  min5_change: number | null
  volume_ratio: number | null
  turnover_rate: number | null
  amount_yi: number | null
  total_mv_yi: number | null
  circ_mv_yi: number | null
  pe: number | null
  pb: number | null
  // 技术指标
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  ma5_bias: number | null
  ma20_bias: number | null
  ma60_bias: number | null
  macd_dif: number | null
  macd_dea: number | null
  macd_hist: number | null
  rsi14: number | null
  boll_position: number | null
  pct_5d: number | null
  pct_20d: number | null
  pct_60d: number | null
  pct_60d_drawdown: number | null
  pct_ytd: number | null
  avg_amount_20d_yi: number | null
  avg_turnover_5d: number | null
  avg_turnover_20d: number | null
}

/** 新闻数据项 */
export interface NewsDataItem {
  code: string
  title: string
  url: string
  source: string
  publish_time: string
}

/** 采集响应 */
export interface CollectResponse {
  stocks: StockDataItem[]
  news: NewsDataItem[]
  warnings: string[]
  collected_at: string
  total_stocks: number
  total_news: number
}

/** 采集请求 */
export interface CollectRequest {
  stock_codes?: string[]
  include_news?: boolean
  news_limit?: number
  hist_days?: number
}

export const dataCollectionApi = {
  /** 一键采集数据 */
  collect: (payload: CollectRequest) =>
    ApiClient.post<CollectResponse>('/api/data-collection/collect', payload, { timeout: 180000 }),
}
