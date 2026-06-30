<template>
  <Transition name="status-slide">
    <div
      v-if="showStatus"
      class="network-status"
      :class="statusType"
    >
      <div class="status-card">
        <div class="status-header">
          <el-icon class="status-icon"><component :is="statusIcon" /></el-icon>
          <span class="status-title">{{ statusTitle }}</span>
        </div>
        <div class="status-message">{{ statusMessage }}</div>
        <div v-if="!appStore.isOnline || !appStore.apiConnected" class="status-actions">
          <el-button
            type="primary"
            size="small"
            round
            @click="retryConnection"
            :loading="retrying"
          >
            重试连接
          </el-button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { WarningFilled, CircleCloseFilled } from '@element-plus/icons-vue'

const appStore = useAppStore()
const retrying = ref(false)

// 只在以下情况显示状态：
// 1. 浏览器离线（立即显示）
// 2. 首次API检查已完成 且 连接失败（避免初始化阶段误报）
const showStatus = computed(() => {
  if (!appStore.isOnline) return true
  // 首次健康检查未完成前不显示"后端连接失败"，避免页面加载时误报
  if (!appStore.apiCheckInitialized) return false
  return !appStore.apiConnected
})

// 状态类型：network（网络断开）/ api（后端连接失败）
const statusType = computed<'network' | 'api'>(() => {
  return !appStore.isOnline ? 'network' : 'api'
})

// 状态图标
const statusIcon = computed(() => {
  return !appStore.isOnline ? WarningFilled : CircleCloseFilled
})

// 状态标题
const statusTitle = computed(() => {
  return !appStore.isOnline ? '网络连接已断开' : '后端服务连接失败'
})

// 状态描述
const statusMessage = computed(() => {
  return !appStore.isOnline
    ? '请检查您的网络连接'
    : '无法连接到后端服务，请检查服务是否正常运行'
})

// 重试连接
const retryConnection = async () => {
  retrying.value = true
  try {
    await appStore.checkApiConnection()
    if (appStore.apiConnected) {
      console.log('✅ API连接恢复')
    }
  } catch (error) {
    console.error('❌ 重试连接失败:', error)
  } finally {
    retrying.value = false
  }
}

// 定期检查API连接状态
let checkInterval: number | null = null

onMounted(() => {
  // 每30秒检查一次API连接状态
  checkInterval = window.setInterval(() => {
    if (appStore.isOnline && !appStore.apiConnected) {
      appStore.checkApiConnection()
    }
  }, 30000)
})

onUnmounted(() => {
  if (checkInterval) {
    clearInterval(checkInterval)
  }
})
</script>

<style scoped>
/* 定位：左下角固定浮动 */
.network-status {
  position: fixed;
  left: 20px;
  bottom: 20px;
  z-index: 9999;
  max-width: 340px;
}

/* 玻璃拟态卡片 */
.status-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 18px;
  border-radius: var(--glass-radius-lg);
  background: var(--glass-bg-surface-strong);
  border: 1px solid var(--glass-stroke-base);
  border-left: 4px solid var(--el-color-warning);
  box-shadow: var(--glass-shadow-lg);
  backdrop-filter: blur(var(--glass-blur-lg)) saturate(1.6);
  -webkit-backdrop-filter: blur(var(--glass-blur-lg)) saturate(1.6);
}

/* 状态色调：后端连接失败 = danger，网络断开 = warning */
.network-status.api .status-card {
  border-left-color: var(--el-color-danger);
}

/* 标题行：图标 + 标题横向排列 */
.status-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.network-status.api .status-icon {
  color: var(--el-color-danger);
}

.network-status.network .status-icon {
  color: var(--el-color-warning);
}

.status-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--glass-text-primary);
  line-height: 1.3;
}

/* 描述文案 */
.status-message {
  font-size: 13px;
  line-height: 1.5;
  color: var(--glass-text-secondary);
}

/* 按钮区：居中对齐 */
.status-actions {
  display: flex;
  justify-content: center;
  margin-top: 2px;
}

/* 滑入/滑出动画 */
.status-slide-enter-active,
.status-slide-leave-active {
  transition: all 0.3s ease;
}

.status-slide-enter-from,
.status-slide-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

/* 窄屏自适应 */
@media (max-width: 480px) {
  .network-status {
    left: 12px;
    right: 12px;
    bottom: 12px;
    max-width: none;
  }
}
</style>
