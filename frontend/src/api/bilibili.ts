import { ApiClient } from './request'

/** UP 主动态项 */
export interface BiliDynamic {
  id: string
  type: string
  pub_ts: number
  pub_time: string
  text: string
  title: string
  video_bvid: string
}

/** LLM 提取的股票观点 */
export interface BiliStockOpinion {
  stock_name: string
  stock_code: string
  sentiment: string  // 看多/看空/中性/观望
  mention: string
  dynamic_id: string
  pub_time: string
}

/** UP 主（含动态和股票提取） */
export interface UpmasterItem {
  mid: string
  uname: string
  category?: string
  notes?: string
  added_at?: string
  dynamics?: BiliDynamic[]
  stocks?: BiliStockOpinion[]
  fetch_error?: string | null
}

export interface AddUpmasterReq {
  mid: string
  uname?: string
  category?: string
  notes?: string
}

export interface UpmasterSearchResult {
  mid: string
  uname: string
  face: string
  sign: string
}

export const bilibiliApi = {
  /** 获取 UP 主列表（含动态+股票提取） */
  list: () => ApiClient.get<UpmasterItem[]>('/api/bilibili/'),

  /** 添加 UP 主 */
  add: (payload: AddUpmasterReq) => ApiClient.post('/api/bilibili/', payload),

  /** 移除 UP 主 */
  remove: (mid: string) => ApiClient.delete(`/api/bilibili/${mid}`),

  /** 更新备注/分类 */
  update: (mid: string, payload: { category?: string; notes?: string }) =>
    ApiClient.put(`/api/bilibili/${mid}`, payload),

  /** 根据 UID 查询 UP 主信息（添加前预览） */
  searchUp: (mid: string) => ApiClient.get<UpmasterSearchResult>('/api/bilibili/search-up', { mid }),
}
