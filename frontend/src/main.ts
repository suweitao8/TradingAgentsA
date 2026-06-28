import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import zhCn from 'element-plus/es/locale/lang/zh-cn'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'

import App from './App.vue'
import router from './router'
import { setupGlobalComponents } from './components'
import { useAppStore } from '@/stores/app'
import './styles/index.scss'
import './styles/dark-theme.scss'

// 创建应用实例
const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 使用插件
const pinia = createPinia()
app.use(pinia)
app.use(router)
// 设置全局中文 locale（Element Plus）
dayjs.locale('zh-cn')
app.use(ElementPlus, {
  size: 'default',
  zIndex: 3000,
  locale: zhCn,
  // 配置消息提示
  message: {
    max: 3, // 最多同时显示3个消息
    grouping: true, // 启用消息分组，相同内容的消息不会重复显示
    duration: 3000, // 默认显示时长3秒
  },
})

// 注册全局组件
setupGlobalComponents(app)

// 全局错误处理
app.config.errorHandler = (err, _vm, info) => {
  console.error('[App] 全局错误:', err, info)
}

// 全局警告处理
app.config.warnHandler = (msg, _vm, trace) => {
  // 仅在开发环境输出警告，减少生产环境噪音
  if (import.meta.env.DEV) {
    console.warn('[App] 警告:', msg, trace)
  }
}

// 初始化应用
const initApp = async () => {
  try {
    const appStore = useAppStore()

    // 应用主题
    appStore.applyTheme()

    // 设置网络状态监听
    window.addEventListener('online', () => {
      appStore.setOnlineStatus(true)
      appStore.checkApiConnection()
    })

    window.addEventListener('offline', () => {
      appStore.setOnlineStatus(false)
      appStore.setApiConnected(false)
    })

    // 检查API连接状态
    await appStore.checkApiConnection()

    // 单用户本地部署模式：无需认证状态检查与 token 刷新
  } catch (error) {
    const err = error as { code?: string; message?: string }
    console.warn('[App] 初始化失败，应用仍将继续启动:', err.message || err)
  } finally {
    // 无论认证状态如何，都挂载应用
    app.mount('#app')
  }
}

// 启动应用
initApp()
