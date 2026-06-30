/**
 * 学习中心共享数据模块
 * 统一管理分类信息、文章列表、文章注册表等数据，消除多组件间的冗余定义。
 */

// 为 Element Plus Tag 的 type 属性定义允许的联合类型
export type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

// ---- 分类信息 ----
export interface CategoryInfo {
  title: string
  icon: string
  description: string
}

export const categoryMap: Record<string, CategoryInfo> = {
  'ai-basics': {
    title: 'AI基础知识',
    icon: '🤖',
    description: '从零开始了解人工智能和大语言模型的基本概念'
  },
  'prompt-engineering': {
    title: '提示词工程',
    icon: '✍️',
    description: '学习如何编写高质量的提示词，让AI更好地理解你的需求'
  },
  'model-selection': {
    title: '模型选择指南',
    icon: '🎯',
    description: '了解不同大模型的特点，选择最适合你的模型'
  },
  'analysis-principles': {
    title: 'AI分析股票原理',
    icon: '📊',
    description: '深入了解多智能体如何协作分析股票'
  },
  'risks-limitations': {
    title: '风险与局限性',
    icon: '⚠️',
    description: '了解AI的潜在问题和正确使用方式'
  },
  'resources': {
    title: '源项目与论文',
    icon: '📖',
    description: 'TradingAgents项目介绍和学术论文资源'
  },
  'tutorials': {
    title: '实战教程',
    icon: '🎓',
    description: '通过实际案例学习如何使用本工具'
  },
  'faq': {
    title: '常见问题',
    icon: '❓',
    description: '快速找到常见问题的答案'
  }
}

// ---- 分类顺序（用于首页卡片排列）----
export const categoryOrder: string[] = [
  'ai-basics',
  'prompt-engineering',
  'model-selection',
  'analysis-principles',
  'risks-limitations',
  'resources',
  'tutorials',
  'faq'
]

// ---- 文章列表项（分类维度）----
export interface ArticleListItem {
  id: string
  title: string
  description: string
  readTime: string
  views: number
  difficulty: TagType
  difficultyText: string
}

export const articlesDatabase: Record<string, ArticleListItem[]> = {
  'ai-basics': [
    {
      id: 'what-is-llm',
      title: '什么是大语言模型（LLM）？',
      description: '深入了解大语言模型的定义、工作原理和在股票分析中的应用',
      readTime: '10分钟',
      views: 2345,
      difficulty: 'success',
      difficultyText: '入门'
    }
  ],
  'prompt-engineering': [
    {
      id: 'prompt-basics',
      title: '提示词基础',
      description: '学习提示词的基本概念、结构和编写技巧',
      readTime: '10分钟',
      views: 1876,
      difficulty: 'success',
      difficultyText: '入门'
    },
    {
      id: 'best-practices',
      title: '提示词工程最佳实践',
      description: '掌握提示词编写的核心原则和实用技巧',
      readTime: '12分钟',
      views: 1543,
      difficulty: 'warning',
      difficultyText: '进阶'
    }
  ],
  'model-selection': [
    {
      id: 'model-comparison',
      title: '大语言模型对比与选择',
      description: '对比主流大语言模型的特点，学会选择最适合的模型',
      readTime: '15分钟',
      views: 1987,
      difficulty: 'warning',
      difficultyText: '进阶'
    }
  ],
  'analysis-principles': [
    {
      id: 'multi-agent-system',
      title: '多智能体系统详解',
      description: '深入理解TradingAgentsA的多智能体协作机制',
      readTime: '15分钟',
      views: 1654,
      difficulty: 'warning',
      difficultyText: '进阶'
    }
  ],
  'risks-limitations': [
    {
      id: 'risk-warnings',
      title: 'AI股票分析的风险与局限性',
      description: '了解AI的主要局限性、使用风险和正确的使用方式',
      readTime: '12分钟',
      views: 2134,
      difficulty: 'success',
      difficultyText: '入门'
    }
  ],
  'resources': [
    {
      id: 'tradingagents-intro',
      title: 'TradingAgents项目介绍',
      description: '了解TradingAgentsA的源项目TradingAgents的架构和特性',
      readTime: '15分钟',
      views: 1432,
      difficulty: 'warning',
      difficultyText: '进阶'
    },
    {
      id: 'paper-guide',
      title: 'TradingAgents论文解读',
      description: '深度解读TradingAgents学术论文的核心内容和创新点',
      readTime: '20分钟',
      views: 987,
      difficulty: 'danger',
      difficultyText: '高级'
    }
  ],
  'tutorials': [
    {
      id: 'getting-started',
      title: '快速入门教程',
      description: '从零开始学习如何使用TradingAgentsA进行股票分析',
      readTime: '10分钟',
      views: 3456,
      difficulty: 'success',
      difficultyText: '入门'
    },
    {
      id: 'usage-guide-preview',
      title: '使用指南（试用版）',
      description: 'TradingAgentsA v1.0.1 使用指南与试用说明',
      readTime: '15分钟',
      views: 1288,
      difficulty: 'success',
      difficultyText: '入门'
    }
  ],
  'faq': [
    {
      id: 'general-questions',
      title: '常见问题解答',
      description: '快速找到关于功能、模型选择、使用技巧等常见问题的答案',
      readTime: '15分钟',
      views: 2876,
      difficulty: 'success',
      difficultyText: '入门'
    }
  ]
}

// ---- 外链文章映射 ----
export const externalMap: Record<string, string> = {
  'getting-started': 'https://mp.weixin.qq.com/s/uAk4RevdJHMuMvlqpdGUEw',
  'usage-guide-preview': 'https://mp.weixin.qq.com/s/ppsYiBncynxlsfKFG8uEbw'
}

// ---- 文章注册表：支持本地 Markdown 或外链 ----
export interface ArticleInfo {
  title: string
  category: string
  categoryType: TagType
  readTime: string
  loader?: () => Promise<any>
  externalUrl?: string
}

export const registry: Record<string, ArticleInfo> = {
  'what-is-llm': { title: '什么是大语言模型（LLM）？', loader: () => import('../../../../docs/learning/01-ai-basics/what-is-llm.md?raw'), category: 'AI基础知识', categoryType: 'primary', readTime: '10分钟' },
  'prompt-basics': { title: '提示词基础', loader: () => import('../../../../docs/learning/02-prompt-engineering/prompt-basics.md?raw'), category: '提示词工程', categoryType: 'success', readTime: '10分钟' },
  'best-practices': { title: '提示词工程最佳实践', loader: () => import('../../../../docs/learning/02-prompt-engineering/best-practices.md?raw'), category: '提示词工程', categoryType: 'success', readTime: '12分钟' },
  'model-comparison': { title: '大语言模型对比与选择', loader: () => import('../../../../docs/learning/03-model-selection/model-comparison.md?raw'), category: '模型选择指南', categoryType: 'warning', readTime: '15分钟' },
  'multi-agent-system': { title: '多智能体系统详解', loader: () => import('../../../../docs/learning/04-analysis-principles/multi-agent-system.md?raw'), category: 'AI分析原理', categoryType: 'info', readTime: '15分钟' },
  'risk-warnings': { title: 'AI股票分析的风险与局限性', loader: () => import('../../../../docs/learning/05-risks-limitations/risk-warnings.md?raw'), category: '风险与局限性', categoryType: 'danger', readTime: '12分钟' },
  'tradingagents-intro': { title: 'TradingAgents项目介绍', loader: () => import('../../../../docs/learning/06-resources/tradingagents-intro.md?raw'), category: '源项目与论文', categoryType: 'primary', readTime: '15分钟' },
  'paper-guide': { title: 'TradingAgents论文解读', loader: () => import('../../../../docs/learning/06-resources/paper-guide.md?raw'), category: '源项目与论文', categoryType: 'primary', readTime: '20分钟' },
  'TradingAgents_论文中文版': { title: 'TradingAgents 论文中文版', loader: () => import('../../../../docs/paper/TradingAgents_论文中文版.md?raw'), category: '源项目与论文', categoryType: 'primary', readTime: '40分钟' },
  // 快速入门改为外链，点击后直接跳转到微信文章
  'getting-started': { title: '快速入门教程（外链）', externalUrl: externalMap['getting-started'], category: '实战教程', categoryType: 'success', readTime: '10分钟' },
  // 使用指南（试用版）外链
  'usage-guide-preview': { title: '使用指南（试用版）', externalUrl: externalMap['usage-guide-preview'], category: '实战教程', categoryType: 'success', readTime: '15分钟' },
  'general-questions': { title: '常见问题解答', loader: () => import('../../../../docs/learning/08-faq/general-questions.md?raw'), category: '常见问题', categoryType: 'info', readTime: '15分钟' }
}

// ---- 文章顺序（用于上一页/下一页）----
export const articleOrder: string[] = [
  'what-is-llm',
  'prompt-basics',
  'best-practices',
  'model-comparison',
  'multi-agent-system',
  'risk-warnings',
  'tradingagents-intro',
  'paper-guide',
  'TradingAgents_论文中文版',
  'getting-started',
  'usage-guide-preview',
  'general-questions'
]

// ---- 工具函数 ----

/** 判断文章是否为外链文章 */
export function isExternalArticle(id: string): boolean {
  return !!externalMap[id]
}

/** 根据文章 id 反查所属分类 slug */
export function findCategoryByArticle(articleId: string): string | null {
  for (const slug in articlesDatabase) {
    if (articlesDatabase[slug].some(a => a.id === articleId)) {
      return slug
    }
  }
  return null
}
