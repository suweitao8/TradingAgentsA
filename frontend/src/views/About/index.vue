<template>
  <div class="about-page">
    <el-card shadow="never" class="about-card">
      <div class="about-header">
        <h1 class="about-title">TradingAgentsA</h1>
        <p class="about-subtitle">AI 驱动的多智能体股票分析平台</p>
        <el-tag size="small" type="info">v{{ appStore.version }}</el-tag>
      </div>

      <el-divider />

      <div class="about-section">
        <p class="about-desc">
          基于 TradingAgents 架构，结合多智能体协作与大语言模型，提供深度股票分析与决策辅助。
        </p>
      </div>

      <el-divider />

      <div class="about-section">
        <h3 class="section-title">相关链接</h3>
        <div class="links">
          <el-link type="primary" :href="repoUrl" target="_blank">GitHub 仓库</el-link>
        </div>
      </div>

      <el-divider />

      <div class="about-section">
        <h3 class="section-title">致谢</h3>
        <p class="about-desc">
          本项目基于 <el-link type="primary" href="https://github.com/TauricResearch/TradingAgents" target="_blank">TauricResearch/TradingAgents</el-link> 开发，感谢原作者的贡献。
        </p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const repoUrl = 'https://github.com/suweitao8/TradingAgentsA'
</script>

<style lang="scss" scoped>
.about-page {
  padding: 24px;
  max-width: 720px;
  margin: 0 auto;
}

.about-card {
  .about-header {
    text-align: center;

    .about-title {
      font-size: 28px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 8px 0;
    }

    .about-subtitle {
      color: var(--el-text-color-regular);
      margin: 0 0 12px 0;
    }
  }

  .about-section {
    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 12px 0;
    }

    .about-desc {
      color: var(--el-text-color-regular);
      line-height: 1.6;
      margin: 0;
    }

    .links {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
  }
}
</style>
