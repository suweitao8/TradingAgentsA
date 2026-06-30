<template>
  <div class="basic-layout">
    <!-- 顶部导航栏 -->
    <TopNav />

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-wrapper">
        <router-view v-slot="{ Component, route }">
          <component :is="Component" :key="route.path" />
        </router-view>
      </div>
    </main>

    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import TopNav from '@/components/Layout/TopNav.vue'
</script>

<style lang="scss" scoped>
.basic-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--glass-page-bg);
  background-attachment: fixed;
}

.main-content {
  flex: 1;
  padding: 24px;
  min-height: calc(100vh - 60px); // 减去 TopNav 高度

  .content-wrapper {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
}
</style>
