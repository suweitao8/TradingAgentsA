<template>
  <nav class="top-nav">
    <div class="nav-inner">
      <!-- 左侧：版本号 -->
      <div class="nav-brand">
        <router-link to="/" class="brand-logo-link" aria-label="返回首页">
          <img class="brand-logo" src="/logo.svg" alt="TradingAgentsA logo" />
        </router-link>
        <span class="version-badge" v-if="appStore.apiVersion">
          <el-icon><MagicStick /></el-icon>
          {{ appStore.apiVersion }}
        </span>
      </div>

      <!-- 中间：导航链接（桌面端）— ETF 在左，自选股在右，竖线分隔 -->
      <div class="nav-links-desktop">
        <router-link
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          class="nav-link"
          :class="{ active: isActive(link) }"
        >
          <el-icon v-if="link.icon"><component :is="link.icon" /></el-icon>
          <span>{{ link.label }}</span>
        </router-link>
      </div>

      <!-- 移动端汉堡菜单 -->
      <el-dropdown trigger="click" @command="onNavCommand" class="nav-mobile-menu">
        <div class="nav-link">
          <el-icon><Menu /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="/bilibili">B站</el-dropdown-item>
            <el-dropdown-item command="/etfs">ETF</el-dropdown-item>
            <el-dropdown-item command="/favorites">股票</el-dropdown-item>
            <el-dropdown-item command="/dashboard" divided>仪表板</el-dropdown-item>
            <el-dropdown-item command="/training">模拟炒股</el-dropdown-item>
            <el-dropdown-item command="/analysis/single">单股分析</el-dropdown-item>
            <el-dropdown-item command="/analysis/batch">批量分析</el-dropdown-item>
            <el-dropdown-item command="/reports">分析报告</el-dropdown-item>
            <el-dropdown-item command="/tasks">任务中心</el-dropdown-item>
            <el-dropdown-item command="/data-collection">数据采集</el-dropdown-item>
            <el-dropdown-item command="/learning" divided>学习中心</el-dropdown-item>
            <el-dropdown-item command="/about">关于</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <!-- 右侧：操作按钮 -->
      <div class="nav-actions">
        <!-- 更多下拉 -->
        <el-dropdown trigger="hover" :hide-on-click="false" @command="onNavCommand">
          <button class="action-btn more-btn" :class="{ active: isMoreActive }">
            <el-icon><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/bilibili">B站</el-dropdown-item>
              <el-dropdown-item command="/dashboard">仪表板</el-dropdown-item>
              <el-dropdown-item command="/training">模拟炒股</el-dropdown-item>
              <el-dropdown-item command="/analysis/single" divided>单股分析</el-dropdown-item>
              <el-dropdown-item command="/analysis/batch">批量分析</el-dropdown-item>
              <el-dropdown-item command="/reports">分析报告</el-dropdown-item>
              <el-dropdown-item command="/tasks" divided>任务中心</el-dropdown-item>
              <el-dropdown-item command="/data-collection">数据采集</el-dropdown-item>
              <el-dropdown-item command="/learning" divided>学习中心</el-dropdown-item>
              <el-dropdown-item command="/about">关于</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- 通知 -->
        <el-tooltip content="通知" placement="bottom">
          <el-badge :value="unreadCount" :hidden="unreadCount === 0">
            <button class="action-btn" @click="openDrawer">
              <el-icon><Bell /></el-icon>
            </button>
          </el-badge>
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
  Star,
  TrendCharts,
  DataAnalysis,
  VideoCamera,
  MoreFilled,
  Menu,
  Bell,
  Setting,
  MagicStick
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const notifStore = useNotificationStore()
const { unreadCount, items } = storeToRefs(notifStore)

// ---- 导航链接 ----
// 主入口：B站、ETF、训练、股票
const navLinks = [
  { path: '/bilibili', label: 'B站', icon: VideoCamera },
  { path: '/etfs', label: 'ETF', icon: TrendCharts },
  { path: '/training', label: '模拟炒股', icon: DataAnalysis },
  { path: '/favorites', label: '股票', icon: Star },
]

const isActive = (link: { path: string }) => {
  return route.path === link.path || route.path.startsWith(link.path + '/')
}

// 「更多」下拉涵盖了仪表板/分析/报告/任务中心/学习中心/数据采集/关于
const isMoreActive = computed(() => {
  return (
    route.path.startsWith('/dashboard') ||
    route.path.startsWith('/analysis') ||
    route.path.startsWith('/reports') ||
    route.path.startsWith('/tasks') ||
    route.path.startsWith('/learning') ||
    route.path.startsWith('/data-collection') ||
    route.path.startsWith('/about')
  )
})

const onNavCommand = (command: string) => {
  router.push(command)
}

// ---- 操作按钮 ----
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
  background: var(--glass-bg-nav);
  // 底部青光分割线（金融科技感）
  border-bottom: 1px solid var(--glass-stroke-soft);
  box-shadow: inset 0 -1px 0 0 rgba(34, 211, 238, 0.08), var(--glass-shadow-nav);
  backdrop-filter: blur(var(--glass-blur-nav)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--glass-blur-nav)) saturate(1.4);
}

.nav-inner {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

// ---- 版本号区 ----
.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;

  .brand-logo-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    line-height: 0;
  }

  .brand-logo {
    width: 28px;
    height: 28px;
    display: block;
  }

  .version-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 999px;
    border: 1px solid var(--glass-stroke-soft);
    background: var(--glass-bg-surface);
    backdrop-filter: blur(var(--glass-blur-sm));
    -webkit-backdrop-filter: blur(var(--glass-blur-sm));
    font-size: 11px;
    font-weight: 600;
    color: var(--glass-text-secondary);
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
  gap: 0;
  flex: 1;
  justify-content: center;

  // 两个链接之间的竖线分隔符
  .nav-link + .nav-link {
    position: relative;
    margin-left: 2px;
    padding-left: 16px;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 1px;
      height: 18px;
      background: var(--glass-stroke-base);
    }
  }
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--glass-radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
  text-decoration: none;

  .el-icon {
    font-size: 16px;
  }

  &:hover {
    color: var(--glass-text-primary);
    background: var(--glass-bg-surface-hover);
  }

  &.active {
    color: var(--glass-text-primary);
    background: var(--glass-bg-surface-hover);
    font-weight: 600;
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
  color: var(--glass-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;

  .el-icon {
    font-size: 18px;
  }

  &:hover {
    background: var(--glass-bg-surface-hover);
    color: var(--accent-cyan);
  }
}

// 「更多」按钮：去掉 hover 圆圈背景
.action-btn.more-btn {
  background: transparent;
  &:hover {
    background: transparent;
  }
  &.active {
    background: transparent;
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
  border-radius: var(--glass-radius-sm);
  border: 1px solid var(--glass-stroke-soft);
  background: var(--glass-bg-surface);
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--glass-stroke-base);
    box-shadow: var(--glass-shadow-sm);
  }
}
.notif-item.unread {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
}
.notif-item .row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--glass-text-tertiary);
  margin-bottom: 4px;
}
.notif-item .title {
  font-weight: 600;
  color: var(--glass-text-primary);
  cursor: pointer;
  margin-bottom: 4px;
}
.notif-item .title:hover {
  text-decoration: underline;
}
.notif-item .content {
  font-size: 12px;
  color: var(--glass-text-secondary);
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
