<template>
  <div class="settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><Setting /></el-icon>
        设置中心
      </h1>
      <p class="page-description">个性化配置、系统管理与运维工具</p>
    </div>

    <!-- 顶部 Tab 导航 -->
    <el-tabs v-model="activeTab" class="settings-tabs" @tab-change="onTabChange">
      <!-- ====== 个人设置 ====== -->
      <el-tab-pane label="通用设置" name="general">
        <el-card shadow="never" class="settings-content">
          <el-form :model="generalSettings" label-width="120px">
            <el-form-item label="语言">
              <el-select v-model="generalSettings.language">
                <el-option label="简体中文" value="zh-CN" />
                <el-option label="English" value="en-US" />
              </el-select>
            </el-form-item>

            <el-form-item label="时区">
              <el-select v-model="generalSettings.timezone">
                <el-option label="北京时间 (UTC+8)" value="Asia/Shanghai" />
                <el-option label="纽约时间 (UTC-5)" value="America/New_York" />
                <el-option label="伦敦时间 (UTC+0)" value="Europe/London" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveGeneralSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="外观设置" name="appearance">
        <el-card shadow="never" class="settings-content">
          <el-form :model="appearanceSettings" label-width="120px">
            <el-form-item label="主题模式">
              <el-radio-group v-model="appearanceSettings.theme" @change="handleThemeChange">
                <el-radio label="light">浅色主题</el-radio>
                <el-radio label="dark">深色主题</el-radio>
                <el-radio label="auto">跟随系统</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveAppearanceSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="分析偏好" name="analysis">
        <el-card shadow="never" class="settings-content">
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
              <el-button type="primary" @click="saveAnalysisSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="通知设置" name="notifications">
        <el-card shadow="never" class="settings-content">
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
              <el-button type="primary" @click="saveNotificationSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- ====== 系统配置 ====== -->
      <el-tab-pane label="配置管理" name="config" lazy>
        <ConfigManagement />
      </el-tab-pane>

      <el-tab-pane label="缓存管理" name="cache" lazy>
        <CacheManagement />
      </el-tab-pane>

      <el-tab-pane label="使用统计" name="usage" lazy>
        <UsageStatistics />
      </el-tab-pane>

      <!-- ====== 系统管理 ====== -->
      <el-tab-pane label="日志中心" name="logs" lazy>
        <OperationLogs />
      </el-tab-pane>

      <el-tab-pane label="数据库管理" name="database" lazy>
        <DatabaseManagement />
      </el-tab-pane>

      <el-tab-pane label="数据源同步" name="sync" lazy>
        <MultiSourceSync />
      </el-tab-pane>

      <el-tab-pane label="定时任务" name="scheduler" lazy>
        <SchedulerManagement />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'
import type { UserPreferences } from '@/types/preferences'
import { Setting } from '@element-plus/icons-vue'
// 系统管理组件（懒加载由 el-tabs lazy 控制）
import ConfigManagement from './ConfigManagement.vue'
import CacheManagement from './CacheManagement.vue'
import UsageStatistics from './UsageStatistics.vue'
import OperationLogs from '@/views/System/OperationLogs.vue'
import DatabaseManagement from '@/views/System/DatabaseManagement.vue'
import MultiSourceSync from '@/views/System/MultiSourceSync.vue'
import SchedulerManagement from '@/views/System/SchedulerManagement.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

// 合法的 tab 名称集合
const validTabs = [
  'general', 'appearance', 'analysis', 'notifications',
  'config', 'cache', 'usage', 'logs', 'database', 'sync', 'scheduler'
]

// 当前激活的标签
const activeTab = ref('general')

// 从路由 query 确定激活 tab
const updateTabFromRoute = () => {
  const tab = route.query.tab as string
  if (tab && validTabs.includes(tab)) {
    activeTab.value = tab
  } else {
    activeTab.value = 'general'
  }
}

// tab 切换时同步到 URL query
const onTabChange = (name: string | number) => {
  const tab = String(name)
  if (tab === 'general') {
    router.replace({ path: '/settings', query: {} })
  } else {
    router.replace({ path: '/settings', query: { tab } })
  }
}

watch(() => [route.path, route.query.tab], updateTabFromRoute, { immediate: true })

// ---- 设置数据 ----
const generalSettings = ref({
  language: appStore.serverPreferences?.language || 'zh-CN',
  timezone: 'Asia/Shanghai'
})

const appearanceSettings = ref({
  theme: appStore.serverPreferences?.ui_theme || 'light'
})

const analysisSettings = ref({
  defaultMarket: appStore.serverPreferences?.default_market || 'A股',
  defaultDepth: appStore.serverPreferences?.default_depth || '3',
  defaultAnalysts: appStore.serverPreferences?.default_analysts || ['市场分析师', '基本面分析师'],
  autoRefresh: appStore.serverPreferences?.auto_refresh ?? true,
  refreshInterval: appStore.serverPreferences?.refresh_interval || 30
})

const notificationSettings = ref({
  desktop: appStore.serverPreferences?.desktop_notifications ?? true,
  analysisComplete: appStore.serverPreferences?.analysis_complete_notification ?? true,
  systemMaintenance: appStore.serverPreferences?.system_maintenance_notification ?? true
})

const buildPreferencesPayload = (
  partial: Partial<UserPreferences>
): UserPreferences => {
  const current = appStore.serverPreferences
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

// 监听服务端偏好变化
watch(() => appStore.serverPreferences, (prefs) => {
  if (prefs) {
    generalSettings.value.language = prefs.language || 'zh-CN'
    appearanceSettings.value.theme = prefs.ui_theme || 'light'
    analysisSettings.value.defaultMarket = prefs.default_market || 'A股'
    analysisSettings.value.defaultDepth = prefs.default_depth || '3'
    analysisSettings.value.defaultAnalysts = prefs.default_analysts || ['市场分析师', '基本面分析师']
    analysisSettings.value.autoRefresh = prefs.auto_refresh ?? true
    analysisSettings.value.refreshInterval = prefs.refresh_interval || 30
    notificationSettings.value.desktop = prefs.desktop_notifications ?? true
    notificationSettings.value.analysisComplete = prefs.analysis_complete_notification ?? true
    notificationSettings.value.systemMaintenance = prefs.system_maintenance_notification ?? true
  }
}, { deep: true })

// ---- 保存方法 ----
const handleThemeChange = (theme: string | number | boolean | undefined) => {
  if (typeof theme === 'string') {
    appStore.setTheme(theme as any)
  }
}

const saveGeneralSettings = async () => {
  try {
    appStore.setLanguage(generalSettings.value.language as any)
    const success = await appStore.savePreferences(
      buildPreferencesPayload({ language: generalSettings.value.language })
    )
    if (success) ElMessage.success('通用设置已保存')
  } catch (error) {
    console.error('保存通用设置失败:', error)
    ElMessage.error('保存通用设置失败')
  }
}

const saveAppearanceSettings = async () => {
  try {
    appStore.setTheme(appearanceSettings.value.theme as any)
    const success = await appStore.savePreferences(
      buildPreferencesPayload({ ui_theme: appearanceSettings.value.theme })
    )
    if (success) ElMessage.success('外观设置已保存')
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
    const success = await appStore.savePreferences(
      buildPreferencesPayload({
        default_market: analysisSettings.value.defaultMarket,
        default_depth: analysisSettings.value.defaultDepth,
        default_analysts: analysisSettings.value.defaultAnalysts,
        auto_refresh: analysisSettings.value.autoRefresh,
        refresh_interval: analysisSettings.value.refreshInterval
      })
    )
    if (success) ElMessage.success('分析偏好已保存')
  } catch (error) {
    console.error('保存分析偏好失败:', error)
    ElMessage.error('保存分析偏好失败')
  }
}

const saveNotificationSettings = async () => {
  try {
    const success = await appStore.savePreferences(
      buildPreferencesPayload({
        desktop_notifications: notificationSettings.value.desktop,
        analysis_complete_notification: notificationSettings.value.analysisComplete,
        system_maintenance_notification: notificationSettings.value.systemMaintenance,
        notifications_enabled: notificationSettings.value.desktop || notificationSettings.value.analysisComplete || notificationSettings.value.systemMaintenance
      })
    )
    if (success) ElMessage.success('通知设置已保存')
  } catch (error) {
    console.error('保存通知设置失败:', error)
    ElMessage.error('保存通知设置失败')
  }
}
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

  .settings-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 20px;
    }

    // 懒加载的系统管理组件自带 page-header，适当收窄间距
    :deep(.page-header) {
      margin-bottom: 16px;
    }
  }

  .settings-content {
    min-height: 400px;

    .setting-description {
      margin-left: 8px;
      font-size: 12px;
      color: var(--el-text-color-placeholder);
    }
  }
}
</style>
