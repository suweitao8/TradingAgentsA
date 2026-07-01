<template>
  <div class="watchlist-tabs">
    <div class="tabs-bar">
      <router-link
        v-for="tab in tabs"
        :key="tab.path"
        :to="tab.path"
        class="tab-item"
        :class="{ active: active === tab.key }"
      >
        <el-icon><component :is="tab.icon" /></el-icon>
        <span>{{ tab.label }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Star, TrendCharts } from '@element-plus/icons-vue'

defineProps<{
  active: 'stocks' | 'etfs'
}>()

const tabs = [
  { key: 'stocks', label: '自选股', path: '/favorites', icon: Star },
  { key: 'etfs', label: 'ETF', path: '/etfs', icon: TrendCharts },
] as const
</script>

<style lang="scss" scoped>
.watchlist-tabs {
  margin-bottom: var(--space-lg);
}

.tabs-bar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  background: var(--glass-bg-surface);
  border: 1px solid var(--glass-stroke-base);
  border-radius: var(--glass-radius-md);
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 18px;
  border-radius: var(--glass-radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-secondary);
  text-decoration: none;
  transition: all 0.2s ease;

  .el-icon {
    font-size: 16px;
  }

  &:hover {
    color: var(--glass-text-primary);
    background: var(--glass-bg-surface-hover);
  }

  &.active {
    color: var(--accent-cyan);
    background: var(--accent-cyan-soft);
    font-weight: 600;
  }
}
</style>
