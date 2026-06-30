<template>
  <div class="settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><Setting /></el-icon>
        {{ pageTitle }}
      </h1>
      <p class="page-description">
        {{ pageDescription }}
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
            <!-- 个人设置菜单 -->
            <template v-if="currentSection === 'personal'">
              <el-menu-item index="general">
                <el-icon><User /></el-icon>
                <span>通用设置</span>
              </el-menu-item>
              <el-menu-item index="learning">
                <el-icon><Reading /></el-icon>
                <span>学习中心</span>
              </el-menu-item>
              <el-menu-item index="analysis">
                <el-icon><TrendCharts /></el-icon>
                <span>分析偏好</span>
              </el-menu-item>
              <el-menu-item index="notifications">
                <el-icon><Bell /></el-icon>
                <span>通知设置</span>
              </el-menu-item>
            </template>

            <!-- 系统配置菜单 -->
            <template v-else-if="currentSection === 'config'">
              <el-menu-item index="config">
                <el-icon><Tools /></el-icon>
                <span>配置管理</span>
              </el-menu-item>
              <el-menu-item index="usage">
                <el-icon><DataAnalysis /></el-icon>
                <span>使用统计</span>
              </el-menu-item>
              <el-menu-item index="cache">
                <el-icon><Coin /></el-icon>
                <span>缓存管理</span>
              </el-menu-item>
            </template>

            <!-- 系统管理菜单 -->
            <template v-else-if="currentSection === 'admin'">
              <el-menu-item index="database">
                <el-icon><Monitor /></el-icon>
                <span>数据库管理</span>
              </el-menu-item>
              <el-menu-item index="logs">
                <el-icon><Document /></el-icon>
                <span>操作日志</span>
              </el-menu-item>
              <el-menu-item index="sync">
                <el-icon><Refresh /></el-icon>
                <span>多数据源同步</span>
              </el-menu-item>
            </template>
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
              <el-button type="primary" @click="saveGeneralSettings">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 学习中心 -->
        <el-card v-show="activeTab === 'learning'" class="settings-content" shadow="never">
          <template #header>
            <h3>📚 学习中心</h3>
          </template>

          <p class="learning-subtitle">了解AI、大模型和智能股票分析</p>

          <el-row :gutter="20" class="learning-categories">
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('ai-basics')">
                <div class="card-icon">🤖</div>
                <h3>AI基础知识</h3>
                <p>什么是AI？什么是大模型？了解人工智能的基本概念</p>
                <el-tag type="primary" size="small">1篇文章</el-tag>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('prompt-engineering')">
                <div class="card-icon">✍️</div>
                <h3>提示词工程</h3>
                <p>学习如何编写有效的提示词，让AI更好地理解你的需求</p>
                <el-tag type="success" size="small">2篇文章</el-tag>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('model-selection')">
                <div class="card-icon">🎯</div>
                <h3>模型选择指南</h3>
                <p>了解不同大模型的特点，选择最适合你的模型</p>
                <el-tag type="warning" size="small">1篇文章</el-tag>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('analysis-principles')">
                <div class="card-icon">📊</div>
                <h3>AI分析股票原理</h3>
                <p>深入了解多智能体如何协作分析股票</p>
                <el-tag type="info" size="small">1篇文章</el-tag>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('risks-limitations')">
                <div class="card-icon">⚠️</div>
                <h3>风险与局限性</h3>
                <p>了解AI的潜在问题和正确使用方式</p>
                <el-tag type="danger" size="small">1篇文章</el-tag>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('resources')">
                <div class="card-icon">📖</div>
                <h3>源项目与论文</h3>
                <p>TradingAgents项目介绍和学术论文资源</p>
                <el-tag type="primary" size="small">2篇文章</el-tag>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('tutorials')">
                <div class="card-icon">🎓</div>
                <h3>实战教程</h3>
                <p>通过实际案例学习如何使用本工具</p>
                <el-tag type="success" size="small">2篇文章</el-tag>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" :lg="6">
              <el-card class="category-card" shadow="hover" @click="navigateTo('faq')">
                <div class="card-icon">❓</div>
                <h3>常见问题</h3>
                <p>快速找到常见问题的答案</p>
                <el-tag type="info" size="small">1篇文章</el-tag>
              </el-card>
            </el-col>
          </el-row>

          <div class="recommended-section">
            <h2>🌟 推荐阅读</h2>
            <el-row :gutter="20">
              <el-col :xs="24" :sm="12" :md="8" v-for="article in recommendedArticles" :key="article.id">
                <el-card class="article-card" shadow="hover" @click="openArticle(article.id)">
                  <div class="article-meta">
                    <el-tag :type="article.tagType" size="small">{{ article.category }}</el-tag>
                    <span class="read-time">{{ article.readTime }}</span>
                  </div>
                  <h4>{{ article.title }}</h4>
                  <p>{{ article.description }}</p>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-card>

        <!-- 分析偏好 -->
        <el-card v-show="activeTab === 'analysis'" class="settings-content" shadow="never">
          <template #header>
            <h3>分析偏好</h3>
          </template>
          
          <el-form :model="analysisSettings" label-width="120px">
            <el-form-item label="默认市场">
              <el-select v-model="analysisSettings.defaultMarket">
                <el-option label="A股" value="A股" />              </el-select>
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



        <!-- 配置管理 -->
        <el-card v-show="activeTab === 'config'" class="settings-content" shadow="never">
          <template #header>
            <h3>配置管理</h3>
          </template>

          <div class="config-content">
            <el-alert
              title="配置管理"
              type="info"
              description="管理 LLM 配置、数据源配置和市场分类配置"
              :closable="false"
              style="margin-bottom: 20px;"
            />
            <el-button type="primary" @click="goToConfigManagement">
              进入配置管理
            </el-button>
          </div>
        </el-card>

        <!-- 使用统计 -->
        <el-card v-show="activeTab === 'usage'" class="settings-content" shadow="never">
          <template #header>
            <h3>使用统计</h3>
          </template>

          <div class="cache-content">
            <el-alert
              title="使用统计与计费"
              type="info"
              description="查看模型使用情况、Token 消耗和成本统计"
              :closable="false"
              style="margin-bottom: 20px;"
            />
            <el-button type="primary" @click="goToUsageStatistics">
              查看使用统计
            </el-button>
          </div>
        </el-card>

        <!-- 缓存管理 -->
        <el-card v-show="activeTab === 'cache'" class="settings-content" shadow="never">
          <template #header>
            <h3>缓存管理</h3>
          </template>

          <div class="settings-section">
            <el-alert
              title="缓存管理"
              type="info"
              description="管理系统缓存，清理过期数据"
              :closable="false"
              style="margin-bottom: 20px;"
            />
            <el-button type="primary" @click="goToCacheManagement">
              进入缓存管理
            </el-button>
          </div>
        </el-card>

        <!-- 数据库管理 -->
        <el-card v-show="activeTab === 'database'" class="settings-content" shadow="never">
          <template #header>
            <h3>数据库管理</h3>
          </template>

          <div class="database-content">
            <el-alert
              title="数据库管理"
              type="info"
              description="管理数据库连接、备份和恢复"
              :closable="false"
              style="margin-bottom: 20px;"
            />
            <el-button type="primary" @click="goToDatabaseManagement">
              进入数据库管理
            </el-button>
          </div>
        </el-card>

        <!-- 操作日志 -->
        <el-card v-show="activeTab === 'logs'" class="settings-content" shadow="never">
          <template #header>
            <h3>操作日志</h3>
          </template>

          <div class="logs-content">
            <el-alert
              title="操作日志"
              type="info"
              description="查看系统操作日志和审计记录"
              :closable="false"
              style="margin-bottom: 20px;"
            />
            <el-button type="primary" @click="goToOperationLogs">
              查看操作日志
            </el-button>
          </div>
        </el-card>

        <!-- 多数据源同步 -->
        <el-card v-show="activeTab === 'sync'" class="settings-content" shadow="never">
          <template #header>
            <h3>多数据源同步</h3>
          </template>

          <div class="sync-content">
            <el-alert
              title="多数据源同步"
              type="info"
              description="管理多个数据源的同步配置和状态"
              :closable="false"
              style="margin-bottom: 20px;"
            />
            <el-button type="primary" @click="goToMultiSourceSync">
              进入同步管理
            </el-button>
          </div>
        </el-card>


      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'
import type { UserPreferences } from '@/types/preferences'
import {
  Setting,
  User,
  Reading,
  TrendCharts,
  Bell,
  Tools,
  Monitor,
  Coin,
  Document,
  Refresh,
  DataAnalysis
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

// 当前分组：personal（个人设置）、config（系统配置）、admin（系统管理）
const currentSection = ref('personal')

// 页面标题和描述
const pageTitle = computed(() => {
  switch (currentSection.value) {
    case 'personal':
      return '个人设置'
    case 'config':
      return '系统配置'
    case 'admin':
      return '系统管理'
    default:
      return '设置'
  }
})

const pageDescription = computed(() => {
  switch (currentSection.value) {
    case 'personal':
      return '个性化配置和偏好设置'
    case 'config':
      return 'LLM、数据源、使用统计和缓存配置'
    case 'admin':
      return '数据库、日志和同步管理'
    default:
      return '个性化配置和系统管理'
  }
})

// 响应式数据
const activeTab = ref('general')

// 根据路由路径和 query 参数确定当前分组和默认激活的标签
const updateSectionFromRoute = () => {
  const path = route.path
  const tab = route.query.tab as string

  if (path === '/settings') {
    // 个人设置页面
    currentSection.value = 'personal'
    // 根据 tab 参数切换标签
    if (tab) {
      activeTab.value = tab
    } else {
      activeTab.value = 'general'
    }
  } else if (path === '/settings/config') {
    currentSection.value = 'config'
    activeTab.value = 'config'
  } else if (path === '/settings/usage') {
    currentSection.value = 'config'
    activeTab.value = 'usage'
  } else if (path === '/settings/cache') {
    currentSection.value = 'config'
    activeTab.value = 'cache'
  } else if (path === '/settings/database') {
    currentSection.value = 'admin'
    activeTab.value = 'database'
  } else if (path === '/settings/logs') {
    currentSection.value = 'admin'
    activeTab.value = 'logs'
  } else if (path === '/settings/sync') {
    currentSection.value = 'admin'
    activeTab.value = 'sync'
  }
}

// 监听路由变化（包括 query 参数）
watch(() => [route.path, route.query.tab], updateSectionFromRoute, { immediate: true })

// 从 appStore.serverPreferences 获取用户偏好（使用 computed 实现响应式）
const generalSettings = ref({
  language: appStore.serverPreferences?.language || 'zh-CN',
  timezone: 'Asia/Shanghai',
  theme: appStore.serverPreferences?.ui_theme || 'light'
})

const appearanceSettings = ref({
  theme: appStore.serverPreferences?.ui_theme || 'light',
  sidebarWidth: appStore.serverPreferences?.sidebar_width || 240
})

const analysisSettings = ref({
  defaultMarket: appStore.serverPreferences?.default_market || 'A股',
  defaultDepth: appStore.serverPreferences?.default_depth || '3',
  defaultAnalysts: appStore.serverPreferences?.default_analysts || ['市场分析师', '基本面分析师', '新闻分析师'],
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
    default_analysts: current?.default_analysts || ['市场分析师', '基本面分析师', '新闻分析师'],
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

// 监听服务端偏好变化，同步更新设置
watch(() => appStore.serverPreferences, (prefs) => {
  if (prefs) {
    // 更新通用设置
    generalSettings.value.language = prefs.language || 'zh-CN'
    generalSettings.value.theme = prefs.ui_theme || 'light'

    // 更新外观设置（保留数据供 payload，UI 已合并到通用设置）
    appearanceSettings.value.theme = prefs.ui_theme || 'light'
    appearanceSettings.value.sidebarWidth = prefs.sidebar_width || 240

    // 更新分析偏好
    analysisSettings.value.defaultMarket = prefs.default_market || 'A股'
    analysisSettings.value.defaultDepth = prefs.default_depth || '3'
    analysisSettings.value.defaultAnalysts = prefs.default_analysts || ['市场分析师', '基本面分析师', '新闻分析师']
    analysisSettings.value.autoRefresh = prefs.auto_refresh ?? true
    analysisSettings.value.refreshInterval = prefs.refresh_interval || 30

    // 更新通知设置
    notificationSettings.value.desktop = prefs.desktop_notifications ?? true
    notificationSettings.value.analysisComplete = prefs.analysis_complete_notification ?? true
    notificationSettings.value.systemMaintenance = prefs.system_maintenance_notification ?? true
  }
}, { deep: true })

// 方法
const handleMenuSelect = (index: string) => {
  activeTab.value = index
}

const saveGeneralSettings = async () => {
  try {
    // 更新本地 store（立即生效）
    appStore.setLanguage(generalSettings.value.language as any)
    appStore.setTheme(generalSettings.value.theme as any)

    // 保存到后端
    const success = await appStore.savePreferences(
      buildPreferencesPayload({
        language: generalSettings.value.language,
        ui_theme: generalSettings.value.theme
      })
    )

    if (success) {
      ElMessage.success('通用设置已保存')
    }
  } catch (error) {
    console.error('保存通用设置失败:', error)
    ElMessage.error('保存通用设置失败')
  }
}

const saveAnalysisSettings = async () => {
  try {
    // 更新本地 store（立即生效）
    appStore.updatePreferences({
      defaultMarket: analysisSettings.value.defaultMarket as any,
      defaultDepth: analysisSettings.value.defaultDepth as any,
      autoRefresh: analysisSettings.value.autoRefresh,
      refreshInterval: analysisSettings.value.refreshInterval
    })

    // 保存到后端
    const success = await appStore.savePreferences(
      buildPreferencesPayload({
        default_market: analysisSettings.value.defaultMarket,
        default_depth: analysisSettings.value.defaultDepth,
        default_analysts: analysisSettings.value.defaultAnalysts,
        auto_refresh: analysisSettings.value.autoRefresh,
        refresh_interval: analysisSettings.value.refreshInterval
      })
    )

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
    // 保存到后端
    const success = await appStore.savePreferences(
      buildPreferencesPayload({
        desktop_notifications: notificationSettings.value.desktop,
        analysis_complete_notification: notificationSettings.value.analysisComplete,
        system_maintenance_notification: notificationSettings.value.systemMaintenance,
        notifications_enabled: notificationSettings.value.desktop || notificationSettings.value.analysisComplete || notificationSettings.value.systemMaintenance
      })
    )

    if (success) {
      ElMessage.success('通知设置已保存')
    }
  } catch (error) {
    console.error('保存通知设置失败:', error)
    ElMessage.error('保存通知设置失败')
  }
}

// ---- 学习中心 ----
type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

interface RecommendedArticle {
  id: string
  category: string
  tagType: TagType
  title: string
  description: string
  readTime: string
}

const recommendedArticles = ref<RecommendedArticle[]>([
  {
    id: 'what-is-llm',
    category: 'AI基础',
    tagType: 'primary',
    title: '什么是大语言模型（LLM）？',
    description: '从零开始了解大语言模型的基本概念和工作原理',
    readTime: '10分钟'
  },
  {
    id: 'multi-agent-system',
    category: 'AI分析',
    tagType: 'info',
    title: '多智能体系统详解',
    description: '了解本工具如何通过多个AI智能体协作分析股票',
    readTime: '15分钟'
  },
  {
    id: 'best-practices',
    category: '提示词',
    tagType: 'success',
    title: '提示词工程最佳实践',
    description: '学习如何编写高质量的提示词，提升AI分析效果',
    readTime: '12分钟'
  }
])

const navigateTo = (category: string) => {
  router.push(`/learning/${category}`)
}

const openArticle = (articleId: string) => {
  const extMap: Record<string, string> = {
    'getting-started': 'https://mp.weixin.qq.com/s/uAk4RevdJHMuMvlqpdGUEw',
    'usage-guide-preview': 'https://mp.weixin.qq.com/s/ppsYiBncynxlsfKFG8uEbw'
  }
  const external = extMap[articleId]
  if (external) {
    window.open(external, '_blank')
    return
  }
  router.push(`/learning/article/${articleId}`)
}

// 导航函数
const goToConfigManagement = () => {
  router.push('/settings/config')
}

const goToUsageStatistics = () => {
  router.push('/settings/usage')
}

const goToCacheManagement = () => {
  router.push('/settings/cache')
}

const goToDatabaseManagement = () => {
  router.push('/settings/database')
}

const goToOperationLogs = () => {
  router.push('/settings/logs')
}

const goToMultiSourceSync = () => {
  router.push('/settings/sync')
}



// 生命周期
onMounted(() => {
  // 从store加载设置
  generalSettings.value.theme = appStore.theme
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

    .about-content {
      .system-info,
      .system-status,
      .links {
        margin-bottom: 32px;

        h4 {
          margin: 0 0 16px 0;
          color: var(--el-text-color-primary);
        }

        p {
          margin: 8px 0;
          color: var(--el-text-color-regular);
        }
      }

      .links {
        .el-link {
          margin-right: 16px;
          margin-bottom: 8px;
        }
      }
    }

    /* 学习中心 */
    .learning-subtitle {
      color: var(--el-text-color-regular);
      margin: 0 0 24px 0;
    }

    .learning-categories {
      margin-bottom: 32px;

      .category-card {
        cursor: pointer;
        transition: all 0.3s ease;
        height: 220px;
        margin-bottom: 20px;
        background: var(--el-fill-color-blank);
        border-color: var(--el-border-color);

        &:hover {
          transform: translateY(-6px);
          box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
        }

        .card-icon {
          font-size: 40px;
          text-align: center;
          margin-bottom: 12px;
        }

        h3 {
          font-size: 16px;
          margin-bottom: 8px;
          color: var(--el-text-color-primary);
        }

        p {
          font-size: 13px;
          color: var(--el-text-color-regular);
          margin-bottom: 12px;
          line-height: 1.5;
          min-height: 50px;
        }
      }
    }

    .recommended-section {
      margin-top: 32px;

      h2 {
        font-size: 18px;
        margin-bottom: 16px;
        color: var(--el-text-color-primary);
      }

      .article-card {
        cursor: pointer;
        transition: all 0.3s ease;
        margin-bottom: 16px;

        &:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }

        .article-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;

          .read-time {
            font-size: 12px;
            color: var(--el-text-color-placeholder);
          }
        }

        h4 {
          font-size: 15px;
          margin-bottom: 6px;
          color: var(--el-text-color-primary);
        }

        p {
          font-size: 13px;
          color: var(--el-text-color-regular);
          line-height: 1.5;
        }
      }
    }
  }
}
</style>
