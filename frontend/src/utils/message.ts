/**
 * 统一消息提示工具
 *
 * 错误类提示统一用 ElNotification 展示在屏幕【左下角】，
 * 避免顶部 ElMessage 横条遮挡页面中间的操作区域（如表单/选择器）。
 *
 * 成功 / 警告 / 信息类提示仍走 ElMessage（顶部），本项目不动。
 */

import { ElNotification } from 'element-plus'
import type { NotificationDuration, NotificationOptions } from 'element-plus'

/** 3 秒内相同错误文案不重复弹出（去重） */
const recentErrorMessages = new Map<string, number>()
const ERROR_THROTTLE_TIME = 3000

export interface ShowErrorOptions {
  /** 显示时长（毫秒），0 = 不自动关闭。默认 4500ms */
  duration?: number
  /** 是否跳过去重（默认 false，即默认去重） */
  dedupe?: boolean
  /** 标题，默认"错误" */
  title?: string
}

/**
 * 在屏幕左下角弹出错误通知。
 *
 * 用法：
 *   showError('保存失败')                                // 简单文案
 *   showError('PDF/Word 导出需要安装 pandoc 工具', { duration: 5000 })  // 自定义时长
 *
 * @param message 错误文案（必填）
 * @param options 可选配置
 */
export const showError = (message: string, options: ShowErrorOptions = {}): void => {
  const { duration = 4500, dedupe = false, title = '错误' } = options

  // 去重：3 秒内相同文案不重复弹（可被 options.dedupe=true 关闭）
  if (!dedupe) {
    const now = Date.now()
    const lastTime = recentErrorMessages.get(message)
    if (lastTime && now - lastTime < ERROR_THROTTLE_TIME) {
      return
    }
    recentErrorMessages.set(message, now)

    // 清理过期记录，避免 Map 无限增长
    if (recentErrorMessages.size > 50) {
      const entries = Array.from(recentErrorMessages.entries())
      entries.sort((a, b) => a[1] - b[1])
      entries.slice(0, 25).forEach(([key]) => recentErrorMessages.delete(key))
    }
  }

  ElNotification({
    title,
    message,
    type: 'error',
    position: 'bottom-left',
    duration: duration as NotificationDuration,
    showClose: true,
  } as NotificationOptions)
}
