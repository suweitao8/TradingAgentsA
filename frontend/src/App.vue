<template>
  <div id="app" class="app-container">
    <!-- 网络状态指示器 -->
    <NetworkStatus />

    <!-- 主要内容区域 -->
    <!--
      注意：此处仅渲染顶层路由组件（BasicLayout / Login / 404 等）。
      不对顶层 router-view 添加 transition / keep-alive / key，
      否则在同布局页面间切换时，整个 BasicLayout（含侧边栏、顶栏）会被销毁重建，
      造成"整页刷新"的视觉闪烁。页面过渡动画由 BasicLayout 内部的 router-view 负责。
    -->
    <router-view />

    <!-- 配置向导 -->
    <ConfigWizard
      v-model="showConfigWizard"
      @complete="handleWizardComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NetworkStatus from '@/components/NetworkStatus.vue'
import axios from 'axios'
import { configApi } from '@/api/config'

// 配置向导
const showConfigWizard = ref(false)

// 检查是否需要显示配置向导
const checkFirstTimeSetup = async () => {
  try {
    // 检查是否已经完成过配置向导
    const wizardCompleted = localStorage.getItem('config_wizard_completed')
    if (wizardCompleted === 'true') {
      return
    }

    // 验证配置完整性
    const response = await axios.get('/api/system/config/validate')
    if (response.data.success) {
      const result = response.data.data

      // 如果有缺少的必需配置，显示配置向导
      if (!result.success && result.missing_required?.length > 0) {
        // 延迟显示，等待页面加载完成
        setTimeout(() => {
          showConfigWizard.value = true
        }, 1000)
      }
    }
  } catch (error) {
    console.error('检查配置失败:', error)
  }
}

// 配置向导完成处理
const handleWizardComplete = async (data: any) => {
  try {
    console.log('配置向导数据:', data)

    // 1. 保存大模型配置
    if (data.llm?.provider && data.llm?.apiKey) {
      try {
        // 先添加厂家（如果不存在）
        const providerMap: Record<string, { name: string; base_url?: string }> = {
          deepseek: { name: 'DeepSeek', base_url: 'https://api.deepseek.com' },
          dashscope: { name: '通义千问', base_url: 'https://dashscope.aliyuncs.com/api/v1' },
          openai: { name: 'OpenAI', base_url: 'https://api.openai.com/v1' },
          google: { name: 'Google Gemini', base_url: 'https://generativelanguage.googleapis.com/v1' }
        }

        const providerInfo = providerMap[data.llm.provider]
        if (providerInfo) {
          // 尝试添加厂家（如果已存在会失败，但不影响后续流程）
          try {
            await configApi.addLLMProvider({
              id: data.llm.provider,
              name: data.llm.provider,
              display_name: providerInfo.name,
              default_base_url: providerInfo.base_url,
              is_active: true,
              supported_features: ['chat', 'completion'] // 添加默认支持的功能
            })
          } catch (e) {
            // 厂家可能已存在，忽略错误
            console.log('厂家可能已存在:', e)
          }

          // 添加大模型配置
          if (data.llm.modelName) {
            await configApi.updateLLMConfig({
              provider: data.llm.provider,
              model_name: data.llm.modelName,
              enabled: true
            })

            // 设置为默认大模型
            await configApi.setDefaultLLM(data.llm.modelName)
          }
        }
      } catch (error) {
        console.error('保存大模型配置失败:', error)
        ElMessage.warning('大模型配置保存失败，请稍后在配置管理中手动配置')
      }
    }

    // 2. 保存数据源配置
    if (data.datasource?.type) {
      try {
        const dsConfig: any = {
          name: data.datasource.type,
          type: data.datasource.type,
          enabled: true
        }

        // 根据数据源类型添加认证信息
        if (data.datasource.type === 'tushare' && data.datasource.token) {
          dsConfig.api_key = data.datasource.token
        } else if (data.datasource.type === 'finnhub' && data.datasource.apiKey) {
          dsConfig.api_key = data.datasource.apiKey
        }

        await configApi.addDataSourceConfig(dsConfig)
        await configApi.setDefaultDataSource(data.datasource.type)
      } catch (error) {
        console.error('保存数据源配置失败:', error)
        ElMessage.warning('数据源配置保存失败，请稍后在配置管理中手动配置')
      }
    }

    // 标记配置向导已完成
    localStorage.setItem('config_wizard_completed', 'true')

    ElMessage.success({
      message: '配置完成！欢迎使用股市分析',
      duration: 3000
    })
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存配置失败，请稍后重试')
  }
}

// 生命周期
onMounted(() => {
  // 检查是否需要显示配置向导
  checkFirstTimeSetup()
})
</script>

<style lang="scss">
.app-container {
  min-height: 100vh;
  background: var(--glass-page-bg);
  background-attachment: fixed;
  transition: background 0.3s ease;
}

.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--glass-brand-gradient);
  height: 2px;
}

// 响应式设计
@media (max-width: 768px) {
  .app-container {
    padding: 0;
  }
}
</style>
