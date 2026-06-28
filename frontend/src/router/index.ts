import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 配置NProgress
NProgress.configure({
  showSpinner: false,
  minimum: 0.1,
  easing: 'ease',
  speed: 200,
  trickleSpeed: 100
})

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  // 兼容文档链接：将 /paper/<name>.md 重定向到学习中心文章路由
  {
    path: '/paper/:name.md',
    name: 'PaperMdRedirect',
    redirect: (to) => `/learning/article/${to.params.name as string}`,
    meta: { title: '文档跳转', hideInMenu: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '仪表板',
      icon: 'Dashboard',
    },
    children: [
      {
        path: '',
        name: 'DashboardHome',
        component: () => import('@/views/Dashboard/index.vue'),
        meta: {
          title: '仪表板',
        }
      }
    ]
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/layouts/BasicLayout.vue'),
    redirect: '/analysis/single',
    children: [
      {
        path: 'single',
        name: 'SingleAnalysis',
        component: () => import('@/views/Analysis/SingleAnalysis.vue')
      },
      {
        path: 'batch',
        name: 'BatchAnalysis',
        component: () => import('@/views/Analysis/BatchAnalysis.vue')
      },

    ]
  },
  {
    path: '/screening',
    name: 'StockScreening',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '股票筛选',
      icon: 'Search',
    },
    children: [
      {
        path: '',
        name: 'StockScreeningHome',
        component: () => import('@/views/Screening/index.vue'),
        meta: {
          title: '股票筛选',
        }
      }
    ]
  },

  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '我的自选股',
      icon: 'Star',
    },
    children: [
      {
        path: '',
        name: 'FavoritesHome',
        component: () => import('@/views/Favorites/index.vue'),
        meta: {
          title: '我的自选股',
        }
      }
    ]
  },
  {
    path: '/learning',
    name: 'Learning',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '学习中心',
      icon: 'Reading',
    },
    children: [
      {
        path: '',
        name: 'LearningHome',
        component: () => import('@/views/Learning/index.vue'),
        meta: {
          title: '学习中心',
        }
      },
      {
        path: ':category',
        name: 'LearningCategory',
        component: () => import('@/views/Learning/Category.vue'),
        meta: {
          title: '学习分类',
        }
      },
      {
        path: 'article/:id',
        name: 'LearningArticle',
        component: () => import('@/views/Learning/Article.vue'),
        meta: {
          title: '文章详情',
        }
      }
    ]
  },
  {
    path: '/stocks',
    name: 'Stocks',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '股票详情',
      icon: 'TrendCharts',
      hideInMenu: true
    },
    children: [
      {
        path: ':code',
        name: 'StockDetail',
        component: () => import('@/views/Stocks/Detail.vue'),
        meta: {
          title: '股票详情',
          hideInMenu: true
        }
      }
    ]
  },


  {
    path: '/tasks',
    name: 'TaskCenter',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '任务中心',
      icon: 'List',
    },
    children: [
      {
        path: '',
        name: 'TaskCenterHome',
        component: () => import('@/views/Tasks/TaskCenter.vue'),
        meta: { title: '任务中心' }
      }
    ]
  },
  { path: '/queue', redirect: '/tasks' },
  { path: '/analysis/history', redirect: '/tasks?tab=completed' },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '分析报告',
      icon: 'Document',
    },
    children: [
      {
        path: '',
        name: 'ReportsHome',
        component: () => import('@/views/Reports/index.vue'),
        meta: {
          title: '分析报告',
        }
      },
      {
        path: 'view/:id',
        name: 'ReportDetail',
        component: () => import('@/views/Reports/ReportDetail.vue'),
        meta: {
          title: '报告详情',
        }
      },
      {
        path: 'token',
        name: 'TokenStatistics',
        component: () => import('@/views/Reports/TokenStatistics.vue'),
        meta: {
          title: 'Token统计',
        }
      }
    ]
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '设置',
      icon: 'Setting',
    },
    children: [
      {
        path: '',
        name: 'SettingsHome',
        component: () => import('@/views/Settings/index.vue'),
        meta: {
          title: '设置',
        }
      },
      // 系统管理子页面统一收敛到设置中心 tab，旧链接重定向
      { path: 'config', redirect: { path: '/settings', query: { tab: 'config' } } },
      { path: 'cache', redirect: { path: '/settings', query: { tab: 'cache' } } },
      { path: 'usage', redirect: { path: '/settings', query: { tab: 'usage' } } },
      { path: 'logs', redirect: { path: '/settings', query: { tab: 'logs' } } },
      { path: 'system-logs', redirect: { path: '/settings', query: { tab: 'logs' } } },
      { path: 'database', redirect: { path: '/settings', query: { tab: 'database' } } },
      { path: 'sync', redirect: { path: '/settings', query: { tab: 'sync' } } },
      { path: 'scheduler', redirect: { path: '/settings', query: { tab: 'scheduler' } } },
    ]
  },

  {
    path: '/about',
    name: 'About',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '关于',
      icon: 'InfoFilled',
    },
    children: [
      {
        path: '',
        name: 'AboutHome',
        component: () => import('@/views/About/index.vue'),
        meta: {
          title: '关于',
        }
      }
    ]
  },
  {
    path: '/paper',
    name: 'PaperTrading',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: {
      title: '模拟交易',
      icon: 'CreditCard',
    },
    children: [
      {
        path: '',
        name: 'PaperTradingHome',
        component: () => import('@/views/PaperTrading/index.vue'),
        meta: {
          title: '模拟交易',
        }
      }
    ]
  },

  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/Error/404.vue'),
    meta: {
      title: '页面不存在',
      hideInMenu: true,
    }
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 全局前置守卫
router.beforeEach(async (to, _from, next) => {
  // 开始进度条
  NProgress.start()

  const appStore = useAppStore()

  // 设置页面标题
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - TradingAgentsA`
  }

  // 更新当前路由信息
  appStore.setCurrentRoute(to)

  next()
})

// 全局后置守卫
router.afterEach((_to, _from) => {
  // 结束进度条
  NProgress.done()

  // 页面切换后的处理
  nextTick(() => {
    // 可以在这里添加页面分析、埋点等逻辑
  })
})

// 路由错误处理
// 懒加载 chunk 失效时（dev server 重启、构建更新后浏览器缓存了旧 hash 的 chunk），
// 自动整页刷新一次以丢弃失效缓存；刷新后若仍失败，才提示用户手动处理。
let chunkErrorHandled = false
router.onError((error, to) => {
  console.error('路由错误:', error)
  NProgress.done()
  const message = (error as Error)?.message ?? ''
  const isChunkLoadError =
    message.includes('Failed to fetch dynamically imported module') ||
    message.includes('error loading dynamically imported module') ||
    message.includes('Loading chunk') ||
    message.includes('Loading CSS chunk') ||
    message.includes('Importing a module script failed')
  if (isChunkLoadError && !chunkErrorHandled) {
    // 标记位避免重复刷新死循环；整页刷新后模块重载，标志位自动重置
    chunkErrorHandled = true
    const target = to?.fullPath || window.location.pathname + window.location.search + window.location.hash
    window.location.assign(target)
    return
  }
  // 非 chunk 错误，或刷新后仍失败，提示用户手动处理
  ElMessage.error('页面加载失败，请重试')
})

export default router

// 导出路由配置供其他地方使用
export { routes }
