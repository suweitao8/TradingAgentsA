<template>
  <nav class="top-nav">
    <div class="nav-inner">
      <!-- 左侧：Logo + 版本 -->
      <div class="nav-brand">
        <router-link to="/dashboard" class="brand-link">
          <img src="/logo.svg" alt="TradingAgentsA" class="brand-logo" />
          <span class="brand-text">TradingAgentsA</span>
        </router-link>
        <span class="version-badge">
          <el-icon><MagicStick /></el-icon>
          v{{ appStore.version }}
        </span>
      </div>

      <!-- 中间：导航链接（桌面端） -->
      <div class="nav-links-desktop">
        <router-link
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          class="nav-link"
          :class="{ active: isActive(link) }"
        >
          <el-icon><component :is="link.icon" /></el-icon>
          <span>{{ link.label }}</span>
        </router-link>

        <!-- 股票分析下拉 -->
        <el-dropdown trigger="hover" :hide-on-click="false" @command="onNavCommand">
          <div class="nav-link dropdown-trigger" :class="{ active: isAnalysisActive }">
            <el-icon><TrendCharts /></el-icon>
            <span>股票分析</span>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/analysis/single">单股分析</el-dropdown-item>
              <el-dropdown-item command="/analysis/batch">批量分析</el-dropdown-item>
              <el-dropdown-item command="/reports">分析报告</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- 更多下拉 -->
        <el-dropdown trigger="hover" :hide-on-click="false" @command="onNavCommand">
          <div class="nav-link dropdown-trigger" :class="{ active: isMoreActive }">
            <el-icon><MoreFilled /></el-icon>
            <span>更多</span>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/learning">学习中心</el-dropdown-item>
              <el-dropdown-item command="/about">关于</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 移动端汉堡菜单 -->
      <el-dropdown trigger="click" @command="onNavCommand" class="nav-mobile-menu">
        <div class="nav-link">
          <el-icon><Menu /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="/dashboard">仪表板</el-dropdown-item>
            <el-dropdown-item command="/analysis/single">单股分析</el-dropdown-item>
            <el-dropdown-item command="/analysis/batch">批量分析</el-dropdown-item>
            <el-dropdown-item command="/reports">分析报告</el-dropdown-item>
            <el-dropdown-item command="/tasks">任务中心</el-dropdown-item>
            <el-dropdown-item command="/screening">股票筛选</el-dropdown-item>
            <el-dropdown-item command="/favorites">我的自选股</el-dropdown-item>
            <el-dropdown-item command="/paper">模拟交易</el-dropdown-item>
            <el-dropdown-item command="/learning" divided>学习中心</el-dropdown-item>
            <el-dropdown-item command="/about">关于</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <!-- 右侧：操作按钮 -->
      <div class="nav-actions">
        <!-- 通知 -->
        <el-tooltip content="通知" placement="bottom">
          <el-badge :value="unreadCount" :hidden="unreadCount === 0">
            <button class="action-btn" @click="openDrawer">
              <el-icon><Bell /></el-icon>
            </button>
          </el-badge>
        </el-tooltip>

        <!-- 主题切换 -->
        <el-tooltip :content="themeTooltip" placement="bottom">
          <button class="action-btn" @click="toggleTheme">
            <el-icon>
              <Sunny v-if="appStore.isDarkTheme" />
              <Moon v-else />
            </el-icon>
          </button>
        </el-tooltip>

        <!-- 设置 -->
        <el-tooltip content="设置" placement="bottom">
          <button class="action-btn" @click="goSettings">
            <el-icon><Setting /></el-icon>
          </button>
        </el-tooltip>
      </div>
    </div>

    <!-- 通知抽屉 -->
    <el-drawer v-model="drawerVisible" direction="rtl" size="360px" :with-header="true" title="消息中心">
      <div class="notif-toolbar">
        <el-segmented v-model="filter" :options="[{label: '全部', value: 'all'}, {label: '未读', value: 'unread'}]" size="small" />
        <el-button size="small" text type="primary" @click="onMarkAllRead" :disabled="unreadCount===0">全部已读</el-button>
      </div>
      <el-scrollbar max-height="calc(100vh - 160px)">
        <el-empty v-if="items.length===0" description="暂无通知" />
        <div v-else class="notif-list">
          <div v-for="n in items" :key="n.id" class="notif-item" :class="{unread: n.status==='unread'}">
            <div class="row">
              <el-tag :type="tagType(n.type)" size="small">{{ typeLabel(n.type) }}</el-tag>
              <span class="time">{{ toLocal(n.created_at) }}</span>
            </div>
            <div class="title" @click="go(n)">{{ n.title }}</div>
            <div class="content" v-if="n.content">{{ n.content }}</div>
            <div class="ops">
              <el-button size="small" text type="primary" @click="go(n)" :disabled="!n.link">查看</el-button>
              <el-button size="small" text @click="onMarkRead(n)" v-if="n.status==='unread'">标记已读</el-button>
            </div>
          </div>
        </div>
      </el-scrollbar>
    </el-drawer>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useNotificationStore } from '@/stores/notifications'
import { storeToRefs } from 'pinia'
import {
  Odometer,
  List,
  Search,
  Star,
  CreditCard,
  TrendCharts,
  ArrowDown,
  MoreFilled,
  Menu,
  Bell,
  Sunny,
  Moon,
  Setting,
  MagicStick
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const notifStore = useNotificationStore()
const { unreadCount, items } = storeToRefs(notifStore)

// ---- 导航链接 ----
const navLinks = [
  { path: '/dashboard', label: '仪表板', icon: Odometer },
  { path: '/tasks', label: '任务中心', icon: List },
  { path: '/screening', label: '股票筛选', icon: Search },
  { path: '/favorites', label: '我的自选股', icon: Star },
  { path: '/paper', label: '模拟交易', icon: CreditCard }
]

const isActive = (link: { path: string }) => {
  return route.path === link.path || route.path.startsWith(link.path + '/')
}

const isAnalysisActive = computed(() => {
  return route.path.startsWith('/analysis') || route.path.startsWith('/reports')
})

const isMoreActive = computed(() => {
  return route.path.startsWith('/learning') || route.path.startsWith('/about')
})

const onNavCommand = (command: string) => {
  router.push(command)
}

// ---- 操作按钮 ----
const themeTooltip = computed(() => {
  const map: Record<string, string> = { light: '浅色（点击切换）', dark: '深色（点击切换）', auto: '跟随系统（点击切换）' }
  return map[appStore.theme] || '切换主题'
})

const toggleTheme = () => { appStore.toggleTheme() }

const goSettings = () => {
  router.push('/settings')
}

// ---- 通知抽屉 ----
const drawerVisible = ref(false)
const filter = ref<'all' | 'unread'>('all')
let timerCount: any = null
let timerList: any = null

function openDrawer() {
  drawerVisible.value = true
  notifStore.loadList(filter.value)
}
function onMarkRead(n: any) { notifStore.markRead(n.id) }
function onMarkAllRead() { notifStore.markAllRead() }
function typeLabel(t: string) { return t === 'analysis' ? '分析' : t === 'alert' ? '预警' : '系统' }
function tagType(t: string) { return t === 'analysis' ? 'success' : t === 'alert' ? 'warning' : 'info' }
function toLocal(iso: string) { try { return new Date(iso).toLocaleString() } catch { return iso } }
function go(n: any) { if (n.link) window.open(n.link, '_blank') }

onMounted(() => {
  notifStore.refreshUnreadCount()
  notifStore.connect()

  timerCount = setInterval(() => notifStore.refreshUnreadCount(), 30000)
  watch(drawerVisible, (v) => {
    if (v) {
      notifStore.loadList(filter.value)
      timerList = setInterval(() => notifStore.loadList(filter.value), 60000)
    } else if (timerList) {
      clearInterval(timerList)
      timerList = null
    }
  }, { immediate: true })
  watch(filter, () => { if (drawerVisible.value) notifStore.loadList(filter.value) })
})

onUnmounted(() => {
  if (timerCount) clearInterval(timerCount)
  if (timerList) clearInterval(timerList)
  notifStore.disconnect()
})
</script>

<style lang="scss" scoped>
.top-nav {
  position: sticky;
  top: 0;
  z-index: 999;
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);
  backdrop-filter: blur(8px) saturate(1.2);
  -webkit-backdrop-filter: blur(8px) saturate(1.2);
}

.nav-inner {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  max-width: 1600px;
  margin: 0 auto;
}

// ---- Logo 区 ----
.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;

  .brand-link {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
  }

  .brand-logo {
    width: 28px;
    height: 28px;
  }

  .brand-text {
    font-size: 18px;
    font-weight: 700;
    color: var(--el-text-color-primary);
    white-space: nowrap;
  }

  .version-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 999px;
    border: 1px solid var(--el-border-color);
    background-color: var(--el-fill-color-light);
    font-size: 11px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    white-space: nowrap;

    .el-icon {
      font-size: 12px;
    }
  }
}

// ---- 导航链接 ----
.nav-links-desktop {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: center;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
  text-decoration: none;

  .el-icon {
    font-size: 16px;
  }

  &:hover {
    color: var(--el-color-primary);
    background-color: var(--el-fill-color-light);
  }

  &.active {
    color: var(--el-color-primary);
    background-color: var(--el-color-primary-light-9);
  }

  &.dropdown-trigger {
    .caret {
      font-size: 12px;
      margin-left: -2px;
    }
  }
}

// ---- 操作按钮区 ----
.nav-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.action-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--el-text-color-regular);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;

  .el-icon {
    font-size: 18px;
  }

  &:hover {
    background-color: var(--el-fill-color-light);
    color: var(--el-color-primary);
  }
}

// 移动端汉堡菜单（默认隐藏）
.nav-mobile-menu {
  display: none;
}

// ---- 通知抽屉 ----
.notif-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.notif-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.notif-item {
  padding: 10px 8px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
}
.notif-item.unread {
  background: var(--el-fill-color-light);
}
.notif-item .row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.notif-item .title {
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 4px;
}
.notif-item .title:hover {
  text-decoration: underline;
}
.notif-item .content {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.notif-item .ops {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}

// ---- 响应式 ----
@media (max-width: 1024px) {
  .nav-links-desktop .nav-link span {
    display: none; // 窄屏只显示图标
  }
  .nav-links-desktop .nav-link {
    padding: 8px 10px;
  }
}

@media (max-width: 768px) {
  .nav-links-desktop {
    display: none;
  }
  .nav-mobile-menu {
    display: block;
    flex: 1;
  }
  .brand-text {
    // 保持显示
  }
}
</style>
