import { defineStore } from 'pinia'
import type { RouteLocationNormalized } from 'vue-router'
import { useStorage } from '@vueuse/core'
import { ApiClient } from '@/api/request'
import type { UserPreferences } from '@/types/preferences'

export interface AppState {
  // 应用基础状态
  loading: boolean
  loadingProgress: number
  theme: 'light' | 'dark' | 'auto'
  language: 'zh-CN' | 'en-US'

  // 网络状态
  isOnline: boolean
  apiConnected: boolean
  // 首次健康检查是否完成（完成前不显示连接失败弹窗，避免初始化误报）
  apiCheckInitialized: boolean
  lastApiCheck: number
  // 连续失败计数（避免单次抖动即误报"后端连接失败"）
  apiFailCount: number

  // 布局状态
  sidebarCollapsed: boolean
  sidebarWidth: number

  // 当前路由信息
  currentRoute: RouteLocationNormalized | null

  // 用户偏好（本地缓存，轻量级）
  preferences: {
    defaultMarket: 'A股'
    defaultDepth: '1' | '2' | '3' | '4' | '5'  // 1-5级分析深度
    autoRefresh: boolean
    refreshInterval: number
    showWelcome: boolean
  }

  // 服务端偏好（从后端加载的完整偏好，供设置页读写）
  serverPreferences: UserPreferences | null

  // 系统信息
  version: string
  buildTime: string
  apiVersion: string

  // 服务端偏好设置（单用户本地部署，无账号概念）
  serverPreferences: UserPreferences | null
}

type AppPreferences = AppState['preferences']

const defaultPreferences: AppPreferences = {
  defaultMarket: 'A股',
  defaultDepth: '3',
  autoRefresh: true,
  refreshInterval: 30,
  showWelcome: true
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    loading: false,
    loadingProgress: 0,
    theme: (useStorage('app-theme', 'auto').value || 'auto') as 'light' | 'dark' | 'auto',
    language: (useStorage('app-language', 'zh-CN').value || 'zh-CN') as 'zh-CN' | 'en-US',

    isOnline: navigator.onLine,
    apiConnected: false,
    apiCheckInitialized: false,
    lastApiCheck: 0,
    apiFailCount: 0,

    sidebarCollapsed: useStorage('sidebar-collapsed', false).value || false,
    sidebarWidth: useStorage('sidebar-width', 240).value || 240,

    currentRoute: null,

    preferences: (useStorage<AppPreferences>('user-preferences', defaultPreferences).value || defaultPreferences) as AppPreferences,

    serverPreferences: null,

    version: '0.1.16',
    buildTime: new Date().toISOString(),
    apiVersion: '',

    serverPreferences: null,
  }),

  getters: {
    // 是否为暗色主题
    isDarkTheme(): boolean {
      if (this.theme === 'auto') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches
      }
      return this.theme === 'dark'
    },
    
    // 侧边栏实际宽度
    actualSidebarWidth(): number {
      return this.sidebarCollapsed ? 64 : this.sidebarWidth
    },
    
    // 当前页面标题
    currentPageTitle(): string {
      return this.currentRoute?.meta?.title as string || 'TradingAgentsA'
    },
    
    // 应用信息
    appInfo(): Record<string, any> {
      return {
        version: this.version,
        buildTime: this.buildTime,
        apiVersion: this.apiVersion,
        theme: this.theme,
        language: this.language
      }
    }
  },

  actions: {
    // 设置加载状态
    setLoading(loading: boolean, progress = 0) {
      this.loading = loading
      this.loadingProgress = progress
    },
    
    // 设置加载进度
    setLoadingProgress(progress: number) {
      this.loadingProgress = Math.max(0, Math.min(100, progress))
    },
    
    // 切换主题
    toggleTheme() {
      const themes: Array<'light' | 'dark' | 'auto'> = ['light', 'dark', 'auto']
      const currentIndex = themes.indexOf(this.theme)
      this.theme = themes[(currentIndex + 1) % themes.length]
      this.applyTheme()
    },
    
    // 设置主题
    setTheme(theme: 'light' | 'dark' | 'auto') {
      this.theme = theme
      this.applyTheme()
      // 同步到 localStorage
      localStorage.setItem('app-theme', theme)
    },
    
    // 应用主题
    applyTheme() {
      const isDark = this.isDarkTheme
      document.documentElement.classList.toggle('dark', isDark)
      
      // 更新meta标签
      const themeColorMeta = document.querySelector('meta[name="theme-color"]')
      if (themeColorMeta) {
        themeColorMeta.setAttribute('content', isDark ? '#1f2937' : '#2f7bff')
      }
    },
    
    // 切换语言
    setLanguage(language: 'zh-CN' | 'en-US') {
      this.language = language
      document.documentElement.lang = language
      // 同步到 localStorage
      localStorage.setItem('app-language', language)
    },
    
    // 切换侧边栏
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
    
    // 设置侧边栏状态
    setSidebarCollapsed(collapsed: boolean) {
      this.sidebarCollapsed = collapsed
      // 同步到 localStorage
      localStorage.setItem('sidebar-collapsed', String(collapsed))
    },

    // 设置侧边栏宽度
    setSidebarWidth(width: number) {
      this.sidebarWidth = Math.max(200, Math.min(400, width))
      // 同步到 localStorage
      localStorage.setItem('sidebar-width', String(this.sidebarWidth))
    },
    
    // 设置当前路由
    setCurrentRoute(route: RouteLocationNormalized) {
      this.currentRoute = route
    },
    
    // 更新用户偏好
    updatePreferences(preferences: Partial<AppState['preferences']>) {
      this.preferences = { ...this.preferences, ...preferences }
      // 同步到 localStorage
      localStorage.setItem('user-preferences', JSON.stringify(this.preferences))
    },

    // 重置偏好设置
    resetPreferences() {
      this.preferences = {
        ...defaultPreferences
      }
    },
    
    // 设置网络状态
    setOnlineStatus(isOnline: boolean) {
      this.isOnline = isOnline
    },

    // 设置API连接状态
    setApiConnected(connected: boolean) {
      this.apiConnected = connected
      this.apiCheckInitialized = true
      this.lastApiCheck = Date.now()
    },

    // 检查API连接状态
    // 容错策略：单次失败不立即判断连，连续失败 2 次才报"后端连接失败"，
    // 避免后端偶发慢响应/瞬时抖动导致误报。成功立即恢复。
    // 同时从 /api/health 响应中提取 version，统一版本号来源（后端 VERSION 文件）。
    async checkApiConnection() {
      // 单次健康探测：8s 超时（原 3s 过短，后端偶发慢响应即误报）
      // 返回 [是否成功, 版本号]
      const probe = async (): Promise<[boolean, string]> => {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 8000)
        try {
          const response = await fetch('/api/health', {
            method: 'GET',
            signal: controller.signal
          })
          if (!response.ok) return [false, '']
          const json = await response.json()
          // 后端返回结构 { success, data: { version, ... }, message }
          const ver = json?.data?.version || ''
          return [true, ver]
        } catch {
          return [false, '']
        } finally {
          clearTimeout(timeoutId)
        }
      }

      // 第一次探测
      let [ok, ver] = await probe()
      // 失败则立即重试一次（覆盖瞬时抖动）
      if (!ok) {
        ;[ok, ver] = await probe()
      }

      if (ok) {
        // 成功：清零计数并恢复连接状态；同步版本号（后端 VERSION 文件单一来源）
        this.apiFailCount = 0
        this.setApiConnected(true)
        if (ver) this.apiVersion = ver
        return true
      }

      // 失败：累计计数，连续失败达到阈值才判断连
      this.apiFailCount += 1
      const FAIL_THRESHOLD = 2
      if (this.apiFailCount >= FAIL_THRESHOLD) {
        this.setApiConnected(false)
      } else {
        // 未达阈值：保持当前连接状态不变，避免单次抖动翻转状态
        this.lastApiCheck = Date.now()
      }
      return false
    },

    // 获取API版本信息（已合并到 checkApiConnection，保留方法供兼容调用）
    async fetchApiVersion() {
      await this.checkApiConnection()
    },

    // 重置应用状态
    resetAppState() {
      this.loading = false
      this.loadingProgress = 0
      this.currentRoute = null
    },

    // 从后端加载偏好设置
    async fetchPreferences() {
      try {
        const res = await ApiClient.get('/api/settings/preferences')
        if (res.success && res.data) {
          this.serverPreferences = res.data as UserPreferences
          this.applyServerPreferences(res.data)
        }
      } catch (error) {
        console.warn('⚠️ 加载偏好设置失败，使用默认值', error)
      }
    },

    // 保存偏好设置到后端
    async savePreferences(prefs: Record<string, any>): Promise<boolean> {
      try {
        const res = await ApiClient.put('/api/settings/preferences', prefs)
        if (res.success && res.data) {
          this.serverPreferences = res.data as UserPreferences
          this.applyServerPreferences(res.data)
          return true
        }
        return false
      } catch (error) {
        console.error('更新偏好设置失败:', error)
        return false
      }
    },

    // 将服务端偏好同步到 appStore 本地状态
    applyServerPreferences(prefs: any) {
      if (prefs.ui_theme) {
        this.setTheme(prefs.ui_theme as 'light' | 'dark' | 'auto')
      }
      if (prefs.sidebar_width) {
        this.setSidebarWidth(prefs.sidebar_width)
      }
      if (prefs.language) {
        this.setLanguage(prefs.language as 'zh-CN' | 'en-US')
      }
      if (prefs.default_market || prefs.default_depth || prefs.auto_refresh !== undefined || prefs.refresh_interval) {
        this.updatePreferences({
          defaultMarket: prefs.default_market as any,
          defaultDepth: prefs.default_depth as any,
          autoRefresh: prefs.auto_refresh,
          refreshInterval: prefs.refresh_interval,
        })
      }
    }
  }
})
