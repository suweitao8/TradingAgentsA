<template>
  <div class="settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><Setting /></el-icon>
        个人设置
      </h1>
      <p class="page-description">
        个性化配置和偏好设置
      </p>
    </div>

    <el-row :gutter="24">
      <!-- 左侧：设置菜单 -->
      <el-col :span="6">
        <el-card class="settings-menu" shadow="never">
          <el-menu
            :default-active="activeTab"
            @select="handleMenuSelect"
            class="settings-nav"
          >
            <el-menu-item index="general">
              <el-icon><User /></el-icon>
              <span>通用设置</span>
            </el-menu-item>
            <el-menu-item index="appearance">
              <el-icon><Brush /></el-icon>
              <span>外观设置</span>
            </el-menu-item>
            <el-menu-item index="analysis">
              <el-icon><TrendCharts /></el-icon>
              <span>分析偏好</span>
            </el-menu-item>
            <el-menu-item index="notifications">
              <el-icon><Bell /></el-icon>
              <span>通知设置</span>
            </el-menu-item>
          </el-menu>
        </el-card>
      </el-col>

      <!-- 右侧：设置内容 -->
      <el-col :span="18">
        <!-- 通用设置 -->
        <el-card v-show="activeTab === 'general'" class="settings-content" shadow="never">
          <template #header>
            <h3>通用设置</h3>
          </template>

          <el-form :model="generalSettings" label-width="120px">
            <el-form-item label="用户名">
              <el-input v-model="generalSettings.username" disabled />
            </el-form-item>

            <el-form-item label="邮箱">
              <el-input v-model="generalSettings.email" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveGeneralSettings">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 外观设置 -->
        <el-card v-show="activeTab === 'appearance'" class="settings-content" shadow="never">
          <template #header>
            <h3>外观设置</h3>
          </template>

          <el-form :model="appearanceSettings" label-width="120px">
            <el-form-item label="主题模式">
              <el-radio-group v-model="appearanceSettings.theme" @change="handleThemeChange">
                <el-radio label="light">浅色主题</el-radio>
                <el-radio label="dark">深色主题</el-radio>
                <el-radio label="auto">跟随系统</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="侧边栏宽度">
              <el-slider
                v-model="appearanceSettings.sidebarWidth"
                :min="200"
                :max="400"
                :step="20"
                show-input
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveAppearanceSettings">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 分析偏好 -->
        <el-card v-show="activeTab === 'analysis'" class="settings-content" shadow="never">
          <template #header>
            <h3>分析偏好</h3>
          </template>

          <el-form :model="analysisSettings" label-width="120px">
            <el-form-item label="默认市场">
              <el-select v-model="analysisSettings.defaultMarket">
                <el-option label="A股" value="A股" />
                <el-option label="美股" value="美股" />
                <el-option label="港股" value="港股" />
              </el-select>
            </el-form-item>

            <el-form-item label="默认分析深度">
              <el-select v-model="analysisSettings.defaultDepth">
                <el-option label="1级 - 快速分析" value="1" />
                <el-option label="2级 - 基础分析" value="2" />
                <el-option label="3级 - 标准分析（推荐）" value="3" />
                <el-option label="4级 - 深度分析" value="4" />
                <el-option label="5级 - 全面分析" value="5" />
              </el-select>
            </el-form-item>

            <el-form-item label="默认分析师">
              <el-checkbox-group v-model="analysisSettings.defaultAnalysts">
                <el-checkbox label="市场分析师">市场分析师</el-checkbox>
                <el-checkbox label="基本面分析师">基本面分析师</el-checkbox>
                <el-checkbox label="新闻分析师">新闻分析师</el-checkbox>
                <el-checkbox label="社媒分析师">社媒分析师</el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item label="自动刷新">
              <el-switch v-model="analysisSettings.autoRefresh" />
              <span class="setting-description">自动刷新分析结果</span>
            </el-form-item>

            <el-form-item label="刷新间隔">
              <el-input-number
                v-model="analysisSettings.refreshInterval"
                :min="10"
                :max="300"
                :step="10"
                :disabled="!analysisSettings.autoRefresh"
              />
              <span class="setting-description">秒</span>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveAnalysisSettings">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 通知设置 -->
        <el-card v-show="activeTab === 'notifications'" class="settings-content" shadow="never">
          <template #header>
            <h3>通知设置</h3>
          </template>

          <el-form :model="notificationSettings" label-width="120px">
            <el-form-item label="桌面通知">
              <el-switch v-model="notificationSettings.desktop" />
              <span class="setting-description">显示桌面通知</span>
            </el-form-item>

            <el-form-item label="分析完成通知">
              <el-switch v-model="notificationSettings.analysisComplete" />
            </el-form-item>

            <el-form-item label="系统维护通知">
              <el-switch v-model="notificationSettings.systemMaintenance" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveNotificationSettings">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import type { UserPreferences } from '@/types/auth'
import {
  Setting,
  User,
  Brush,
  TrendCharts,
  Bell
} from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()
const authStore = useAuthStore()

// 响应式数据
const activeTab = ref('general')

// 根据路由 query 参数确定激活的标签
const updateTabFromRoute = () => {
  const tab = route.query.tab as string
  if (tab && ['general', 'appearance', 'analysis', 'notifications'].includes(tab)) {
    activeTab.value = tab
  } else {
    activeTab.value = 'general'
  }
}

// 监听路由变化（包括 query 参数）
watch(() => [route.path, route.query.tab], updateTabFromRoute, { immediate: true })

// 从 authStore 获取用户信息
const generalSettings = ref({
  username: authStore.user?.username || 'admin',
  email: authStore.user?.email || 'admin@example.com'
})

const appearanceSettings = ref({
  theme: authStore.user?.preferences?.ui_theme || 'light',
  sidebarWidth: authStore.user?.preferences?.sidebar_width || 240
})

const analysisSettings = ref({
  defaultMarket: authStore.user?.preferences?.default_market || 'A股',
  defaultDepth: authStore.user?.preferences?.default_depth || '3',
  defaultAnalysts: authStore.user?.preferences?.default_analysts || ['市场分析师', '基本面分析师'],
  autoRefresh: authStore.user?.preferences?.auto_refresh ?? true,
  refreshInterval: authStore.user?.preferences?.refresh_interval || 30
})

const notificationSettings = ref({
  desktop: authStore.user?.preferences?.desktop_notifications ?? true,
  analysisComplete: authStore.user?.preferences?.analysis_complete_notification ?? true,
  systemMaintenance: authStore.user?.preferences?.system_maintenance_notification ?? true
})

const buildPreferencesPayload = (
  partial: Partial<UserPreferences>
): UserPreferences => {
  const current = authStore.user?.preferences
  return {
    default_market: current?.default_market || 'A股',
    default_depth: current?.default_depth || '3',
    default_analysts: current?.default_analysts || ['市场分析师', '基本面分析师'],
    auto_refresh: current?.auto_refresh ?? true,
    refresh_interval: current?.refresh_interval || 30,
    ui_theme: current?.ui_theme || 'light',
    sidebar_width: current?.sidebar_width || 240,
    language: current?.language || 'zh-CN',
    notifications_enabled: current?.notifications_enabled ?? true,
    email_notifications: current?.email_notifications ?? false,
    desktop_notifications: current?.desktop_notifications ?? true,
    analysis_complete_notification: current?.analysis_complete_notification ?? true,
    system_maintenance_notification: current?.system_maintenance_notification ?? true,
    ...partial
  }
}

// 监听用户信息变化，同步更新设置
watch(() => authStore.user, (newUser) => {
  if (newUser) {
    generalSettings.value.username = newUser.username || 'admin'
    generalSettings.value.email = newUser.email || 'admin@example.com'

    appearanceSettings.value.theme = newUser.preferences?.ui_theme || 'light'
    appearanceSettings.value.sidebarWidth = newUser.preferences?.sidebar_width || 240

    analysisSettings.value.defaultMarket = newUser.preferences?.default_market || 'A股'
    analysisSettings.value.defaultDepth = newUser.preferences?.default_depth || '3'
    analysisSettings.value.defaultAnalysts = newUser.preferences?.default_analysts || ['市场分析师', '基本面分析师']
    analysisSettings.value.autoRefresh = newUser.preferences?.auto_refresh ?? true
    analysisSettings.value.refreshInterval = newUser.preferences?.refresh_interval || 30

    notificationSettings.value.desktop = newUser.preferences?.desktop_notifications ?? true
    notificationSettings.value.analysisComplete = newUser.preferences?.analysis_complete_notification ?? true
    notificationSettings.value.systemMaintenance = newUser.preferences?.system_maintenance_notification ?? true
  }
}, { deep: true })

// 方法
const handleMenuSelect = (index: string) => {
  activeTab.value = index
}

const handleThemeChange = (theme: string | number | boolean | undefined) => {
  if (typeof theme === 'string') {
    appStore.setTheme(theme as any)
  }
}

const saveGeneralSettings = async () => {
  try {
    const success = await authStore.updateUserInfo({
      email: generalSettings.value.email,
      preferences: buildPreferencesPayload({})
    })

    if (success) {
      ElMessage.success('通用设置已保存')
    }
  } catch (error) {
    console.error('保存通用设置失败:', error)
    ElMessage.error('保存通用设置失败')
  }
}

const saveAppearanceSettings = async () => {
  try {
    appStore.setSidebarWidth(appearanceSettings.value.sidebarWidth)
    appStore.setTheme(appearanceSettings.value.theme as any)

    const success = await authStore.updateUserInfo({
      preferences: buildPreferencesPayload({
        ui_theme: appearanceSettings.value.theme,
        sidebar_width: appearanceSettings.value.sidebarWidth
      })
    })

    if (success) {
      ElMessage.success('外观设置已保存')
    }
  } catch (error) {
    console.error('保存外观设置失败:', error)
    ElMessage.error('保存外观设置失败')
  }
}

const saveAnalysisSettings = async () => {
  try {
    appStore.updatePreferences({
      defaultMarket: analysisSettings.value.defaultMarket as any,
      defaultDepth: analysisSettings.value.defaultDepth as any,
      autoRefresh: analysisSettings.value.autoRefresh,
      refreshInterval: analysisSettings.value.refreshInterval
    })

    const success = await authStore.updateUserInfo({
      preferences: buildPreferencesPayload({
        default_market: analysisSettings.value.defaultMarket,
        default_depth: analysisSettings.value.defaultDepth,
        default_analysts: analysisSettings.value.defaultAnalysts,
        auto_refresh: analysisSettings.value.autoRefresh,
        refresh_interval: analysisSettings.value.refreshInterval
      })
    })

    if (success) {
      ElMessage.success('分析偏好已保存')
    }
  } catch (error) {
    console.error('保存分析偏好失败:', error)
    ElMessage.error('保存分析偏好失败')
  }
}

const saveNotificationSettings = async () => {
  try {
    const success = await authStore.updateUserInfo({
      preferences: buildPreferencesPayload({
        desktop_notifications: notificationSettings.value.desktop,
        analysis_complete_notification: notificationSettings.value.analysisComplete,
        system_maintenance_notification: notificationSettings.value.systemMaintenance,
        notifications_enabled: notificationSettings.value.desktop || notificationSettings.value.analysisComplete || notificationSettings.value.systemMaintenance
      })
    })

    if (success) {
      ElMessage.success('通知设置已保存')
    }
  } catch (error) {
    console.error('保存通知设置失败:', error)
    ElMessage.error('保存通知设置失败')
  }
}

// 生命周期
onMounted(() => {
  appearanceSettings.value.theme = appStore.theme
  appearanceSettings.value.sidebarWidth = appStore.sidebarWidth

  analysisSettings.value.defaultMarket = appStore.preferences.defaultMarket
  analysisSettings.value.defaultDepth = appStore.preferences.defaultDepth
  analysisSettings.value.autoRefresh = appStore.preferences.autoRefresh
  analysisSettings.value.refreshInterval = appStore.preferences.refreshInterval
})
</script>

<style lang="scss" scoped>
.settings {
  .page-header {
    margin-bottom: 24px;

    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 8px 0;
    }

    .page-description {
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }

  .settings-menu {
    .settings-nav {
      border: none;
    }
  }

  .settings-content {
    min-height: 500px;

    .setting-description {
      margin-left: 8px;
      font-size: 12px;
      color: var(--el-text-color-placeholder);
    }
  }
}
</style>
