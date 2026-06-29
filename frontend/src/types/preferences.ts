// 偏好设置（单用户本地部署模式，无账号概念）
export interface UserPreferences {
  // 分析偏好
  default_market: 'A股' | '美股' | '港股'
  default_depth: '1' | '2' | '3' | '4' | '5'  // 1-5级分析深度
  default_analysts?: string[]  // 默认分析师列表：市场分析师、基本面分析师、新闻分析师
  auto_refresh?: boolean
  refresh_interval?: number

  // 外观设置
  ui_theme: 'light' | 'dark' | 'auto'
  sidebar_width?: number

  // 语言和地区
  language: 'zh-CN' | 'en-US'

  // 通知设置
  notifications_enabled: boolean
  email_notifications: boolean
  desktop_notifications?: boolean
  analysis_complete_notification?: boolean
  system_maintenance_notification?: boolean
}
