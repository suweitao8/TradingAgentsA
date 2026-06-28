import { defineStore } from 'pinia'
import { apiClient } from '@/api/request'
import type { User } from '@/types/auth'

export interface AuthState {
  isAuthenticated: boolean
  user: User | null
  permissions: string[]
  roles: string[]
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => {
    // 单用户本地部署模式：固定管理员身份，无需登录/token
    return {
      isAuthenticated: true,
      user: {
        id: 'admin',
        username: 'admin',
        email: 'admin@local',
        is_admin: true,
      } as User,
      permissions: ['*'],
      roles: ['admin'],
    }
  },

  getters: {
    userAvatar(): string | undefined {
      return this.user?.avatar || undefined
    },
    userDisplayName(): string {
      return this.user?.username || '管理员'
    },
    isAdmin(): boolean {
      return this.roles.includes('admin')
    },
    hasPermission(): (permission: string) => boolean {
      return (_permission: string) => true
    },
    hasRole(): (role: string) => boolean {
      return (role: string) => this.roles.includes(role)
    },
  },

  actions: {
    /**
     * 从后端加载偏好设置并同步到 appStore
     */
    async fetchPreferences() {
      try {
        const res = await apiClient.get('/api/settings/preferences')
        if (res.success && res.data) {
          // 将偏好存入 user.preferences，兼容现有组件读取
          if (this.user) {
            this.user.preferences = res.data
          }
          this.syncPreferencesToAppStore(res.data)
        }
      } catch (error) {
        console.warn('⚠️ 加载偏好设置失败，使用默认值', error)
      }
    },

    /**
     * 更新偏好设置到后端
     */
    async updatePreferences(prefs: Record<string, any>) {
      try {
        const res = await apiClient.put('/api/settings/preferences', prefs)
        if (res.success && res.data) {
          this.syncPreferencesToAppStore(res.data)
          return true
        }
        return false
      } catch (error) {
        console.error('更新偏好设置失败:', error)
        return false
      }
    },

    /**
     * 同步偏好设置到 appStore
     */
    syncPreferencesToAppStore(prefs: any) {
      import('./app').then(({ useAppStore }) => {
        const appStore = useAppStore()

        if (prefs.ui_theme) {
          appStore.setTheme(prefs.ui_theme as 'light' | 'dark' | 'auto')
        }
        if (prefs.sidebar_width) {
          appStore.setSidebarWidth(prefs.sidebar_width)
        }
        if (prefs.language) {
          appStore.setLanguage(prefs.language as 'zh-CN' | 'en-US')
        }
        if (prefs.default_market || prefs.default_depth || prefs.auto_refresh !== undefined || prefs.refresh_interval) {
          appStore.updatePreferences({
            defaultMarket: prefs.default_market as any,
            defaultDepth: prefs.default_depth as any,
            autoRefresh: prefs.auto_refresh,
            refreshInterval: prefs.refresh_interval,
          })
        }

        console.log('✅ 偏好设置已同步到 appStore')
      })
    },
  },
})
