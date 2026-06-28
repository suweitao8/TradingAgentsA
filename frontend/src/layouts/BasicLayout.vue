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

    <!-- 页脚 -->
    <footer class="footer">
      <AppFooter />
    </footer>

    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import TopNav from '@/components/Layout/TopNav.vue'
import AppFooter from '@/components/Layout/AppFooter.vue'
</script>

<style lang="scss" scoped>
.basic-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color-page);
}

.main-content {
  flex: 1;
  padding: 24px;
  min-height: calc(100vh - 60px - 60px); // 减去 TopNav 和 footer 高度

  .content-wrapper {
    max-width: 1400px;
    margin: 0 auto;
  }
}

.footer {
  flex-shrink: 0;
  background-color: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
}
</style>
