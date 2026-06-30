<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="dialogTitle"
    width="92vw"
    top="4vh"
    class="learning-dialog"
    :show-close="true"
    destroy-on-close
    align-center
  >
    <div class="dialog-body">
      <!-- 左侧：文章列表 -->
      <aside class="article-list-panel">
        <div class="panel-header">
          <el-icon><Reading /></el-icon>
          <span>文章列表</span>
          <el-tag size="small" type="info" round>{{ articleList.length }} 篇</el-tag>
        </div>
        <el-scrollbar class="list-scroll">
          <ul class="article-items">
            <li
              v-for="item in articleList"
              :key="item.id"
              class="article-item"
              :class="{ active: currentArticleId === item.id, external: isExternalArticle(item.id) }"
              @click="selectArticle(item.id)"
            >
              <div class="item-title">{{ item.title }}</div>
              <div class="item-meta">
                <el-tag :type="item.difficulty" size="small" effect="plain">{{ item.difficultyText }}</el-tag>
                <span class="item-time">
                  <el-icon><Clock /></el-icon>
                  {{ item.readTime }}
                </span>
              </div>
            </li>
          </ul>
        </el-scrollbar>
      </aside>

      <!-- 右侧：文章内容 -->
      <section class="article-content-panel">
        <!-- 工具栏 -->
        <div class="content-toolbar">
          <div class="article-meta" v-if="article.title">
            <el-tag :type="article.categoryType" size="small">{{ article.category }}</el-tag>
            <span class="meta-item">
              <el-icon><Clock /></el-icon>
              {{ article.readTime }}
            </span>
            <span class="meta-item">
              <el-icon><View /></el-icon>
              {{ article.views }}
            </span>
          </div>
          <el-button
            v-if="article.title"
            type="primary"
            text
            :icon="Download"
            @click="downloadArticle"
            size="small"
          >
            下载
          </el-button>
        </div>

        <el-scrollbar class="content-scroll" ref="contentScrollRef">
          <!-- 加载中 -->
          <div v-if="loading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在加载文章...</span>
          </div>

          <!-- 空状态（尚未选择文章） -->
          <div v-else-if="!article.content" class="empty-state">
            <el-icon :size="48"><Document /></el-icon>
            <p>请从左侧选择一篇文章开始阅读</p>
          </div>

          <!-- 文章正文 -->
          <article v-else class="article-content" v-html="article.content" ref="articleContentRef"></article>
        </el-scrollbar>
      </section>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Clock, View, Reading, Loading, Document } from '@element-plus/icons-vue'
import { marked } from 'marked'
import {
  categoryMap,
  articlesDatabase,
  registry,
  externalMap,
  isExternalArticle
} from './data'
import { showError } from '@/utils/message'

const props = defineProps<{
  modelValue: boolean
  category: string
  articleId?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

// ---- 分类信息 ----
const categoryInfo = computed(() => {
  return categoryMap[props.category] || { title: '未知分类', icon: '📚', description: '' }
})

const dialogTitle = computed(() => `${categoryInfo.value.icon} ${categoryInfo.value.title}`)

// ---- 文章列表 ----
const articleList = computed(() => articlesDatabase[props.category] || [])

// ---- 当前文章 ----
const currentArticleId = ref<string>('')
const loading = ref(false)
const article = ref({
  id: '',
  title: '',
  category: '',
  categoryType: 'primary' as any,
  readTime: '',
  views: 0,
  updateTime: '',
  content: ''
})

const contentScrollRef = ref()
const articleContentRef = ref<HTMLElement>()

// ---- 选择文章 ----
function selectArticle(id: string) {
  // 外链文章：直接新标签打开，不改变右侧内容
  if (isExternalArticle(id)) {
    window.open(externalMap[id], '_blank')
    return
  }
  currentArticleId.value = id
  loadArticle(id)
}

// ---- 加载文章 ----
async function loadArticle(id: string) {
  const info = registry[id]
  if (!info) {
    showError('未找到文章')
    return
  }

  loading.value = true
  article.value = {
    id,
    title: info.title,
    category: info.category,
    categoryType: info.categoryType,
    readTime: info.readTime,
    views: 0,
    updateTime: new Date().toISOString().slice(0, 10),
    content: ''
  }

  try {
    const mod = info.loader ? await info.loader() : ''
    const md: string = typeof mod === 'string' ? mod : (mod.default || '')

    // 解析 markdown -> html，开启标题锚点（兼容中文）
    const renderer = new marked.Renderer()
    renderer.heading = function ({ tokens, depth, text }: any) {
      let htmlText = ''
      if (Array.isArray(tokens) && tokens.length) {
        htmlText = this.parser.parseInline(tokens)
      } else if (typeof text === 'string') {
        htmlText = marked.parseInline(text) as string
      }
      const plain = (htmlText || '').replace(/<[^>]+>/g, '')
      const headingId = plain
        .toLowerCase()
        .replace(/[^\w\u4e00-\u9fa5]+/g, '-')
        .replace(/^-+|-+$/g, '')
      return `<h${depth} class="article-heading" id="${headingId}">${htmlText}</h${depth}>`
    }
    marked.setOptions({ renderer })
    let html = marked.parse(md) as string
    html = convertLocalLinks(html)
    html = rewriteImageSrc(html)
    article.value.content = html
  } catch (e) {
    console.error(e)
    showError('加载文章失败：无法访问文档资源')
  } finally {
    loading.value = false
    await nextTick()
    setupInternalLinks()
    // 滚动到顶部
    contentScrollRef.value?.setScrollTop(0)
  }
}

// ---- 下载文章 ----
async function downloadArticle() {
  if (!article.value.id) return
  const info = registry[article.value.id]
  if (!info) {
    ElMessage.warning('未找到文章资源')
    return
  }
  if (info.externalUrl) {
    window.open(info.externalUrl, '_blank')
    return
  }
  try {
    const mod = info.loader ? await info.loader() : ''
    const md: string = typeof mod === 'string' ? mod : (mod.default || '')
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${article.value.id}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    showError('下载失败')
  }
}

// ---- Markdown 后处理 ----

// 将 markdown 中的本地链接转换为应用内路由链接
function convertLocalLinks(html: string): string {
  const div = document.createElement('div')
  div.innerHTML = html

  const links = div.querySelectorAll('a')
  for (const link of links) {
    const href = link.getAttribute('href')
    if (href && href.endsWith('.md')) {
      const fileName = href.split('/').pop()?.replace('.md', '')
      if (fileName && registry[fileName]) {
        link.setAttribute('href', `/learning/article/${fileName}`)
        link.setAttribute('data-internal', 'true')
      }
    } else if (href && href.endsWith('.pdf')) {
      const fileName = href.split('/').pop() || ''
      if (fileName) {
        const target = href.includes('/paper/') ? `/paper/${fileName}` : `/assets/${fileName}`
        link.setAttribute('href', target)
        link.setAttribute('target', '_blank')
        link.setAttribute('rel', 'noopener noreferrer')
      }
    }
  }

  return div.innerHTML
}

// 将 Markdown 中的图片路径重写为打包后的资源 URL
function rewriteImageSrc(html: string): string {
  const div = document.createElement('div')
  div.innerHTML = html

  const assetMap: Record<string, string> = {
    'assets/schema.png': '/assets/schema.png',
    'assets/analyst.png': '/assets/analyst.png',
    'assets/researcher.png': '/assets/researcher.png',
    'assets/trader.png': '/assets/trader.png',
    'assets/risk.png': '/assets/risk.png'
  }

  const imgs = div.querySelectorAll('img')
  for (const img of imgs) {
    const src = img.getAttribute('src') || ''
    if (src.startsWith('/')) continue
    for (const key in assetMap) {
      if (src.endsWith(key)) {
        img.setAttribute('src', assetMap[key])
        break
      }
    }
  }

  return div.innerHTML
}

// 弹窗内的内部链接：弹窗内可切换的文章直接切换，其余路由跳转
function setupInternalLinks() {
  nextTick(() => {
    const container = articleContentRef.value
    if (!container) return

    const links = container.querySelectorAll('a[data-internal="true"]')
    for (const link of links) {
      link.addEventListener('click', (e) => {
        e.preventDefault()
        const href = link.getAttribute('href') || ''
        // 提取文章 id
        const match = href.match(/\/learning\/article\/(.+)$/)
        if (match) {
          const targetId = match[1]
          // 如果该文章属于当前分类，弹窗内直接切换
          const inCurrentCategory = articleList.value.some(a => a.id === targetId)
          if (inCurrentCategory) {
            selectArticle(targetId)
            return
          }
        }
        // 其余情况回退到路由跳转（关闭弹窗后跳转）
        window.open(href, '_blank')
      })
    }
  })
}

// ---- 弹窗打开时初始化 ----
watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      // 优先使用传入的 articleId，否则选第一篇非外链文章
      const initialId = props.articleId && !isExternalArticle(props.articleId)
        ? props.articleId
        : articleList.value.find(a => !isExternalArticle(a.id))?.id || ''

      if (initialId) {
        currentArticleId.value = initialId
        loadArticle(initialId)
      } else {
        currentArticleId.value = ''
        article.value = {
          id: '', title: '', category: '', categoryType: 'primary',
          readTime: '', views: 0, updateTime: '', content: ''
        }
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
// 弹窗整体样式通过 :deep 穿透 el-dialog
.learning-dialog {
  :deep(.el-dialog__header) {
    padding: 16px 24px;
    margin-right: 0;
    border-bottom: 1px solid var(--glass-stroke-soft);
    .el-dialog__title {
      font-size: 18px;
      font-weight: 700;
      color: var(--glass-text-primary);
    }
  }

  :deep(.el-dialog__body) {
    padding: 0;
    height: calc(85vh - 60px);
  }
}

.dialog-body {
  display: flex;
  height: 100%;
  overflow: hidden;
}

// ---- 左侧文章列表 ----
.article-list-panel {
  width: 300px;
  flex-shrink: 0;
  border-right: 1px solid var(--glass-stroke-soft);
  background: var(--glass-bg-surface);
  display: flex;
  flex-direction: column;

  .panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 16px;
    font-size: 14px;
    font-weight: 600;
    color: var(--glass-text-secondary);
    border-bottom: 1px solid var(--glass-stroke-soft);

    .el-icon {
      font-size: 16px;
    }
  }

  .list-scroll {
    flex: 1;
  }

  .article-items {
    list-style: none;
    margin: 0;
    padding: 8px;
  }

  .article-item {
    padding: 12px 14px;
    border-radius: var(--glass-radius-sm);
    cursor: pointer;
    transition: all 0.2s ease;
    margin-bottom: 4px;

    &:hover {
      background: var(--el-color-primary-light-9);
    }

    &.active {
      background: var(--el-color-primary-light-9);

      .item-title {
        color: var(--el-color-primary);
        font-weight: 600;
      }
    }

    &.external {
      .item-title::after {
        content: ' 🔗';
        font-size: 12px;
      }
    }

    .item-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--glass-text-primary);
      line-height: 1.5;
      margin-bottom: 8px;
    }

    .item-meta {
      display: flex;
      align-items: center;
      gap: 10px;

      .item-time {
        display: flex;
        align-items: center;
        gap: 3px;
        font-size: 12px;
        color: var(--glass-text-tertiary);

        .el-icon {
          font-size: 12px;
        }
      }
    }
  }
}

// ---- 右侧文章内容 ----
.article-content-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--glass-bg-surface-strong);

  .content-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 24px;
    border-bottom: 1px solid var(--glass-stroke-soft);
    flex-shrink: 0;

    .article-meta {
      display: flex;
      align-items: center;
      gap: 16px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        color: var(--glass-text-tertiary);

        .el-icon {
          font-size: 14px;
        }
      }
    }
  }

  .content-scroll {
    flex: 1;
  }

  // 加载中 / 空状态
  .loading-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--glass-text-tertiary);
    font-size: 15px;

    .el-icon {
      color: var(--el-color-primary);
    }
  }

  .loading-state .el-icon {
    font-size: 32px;
  }

  // 文章正文样式
  .article-content {
    padding: 28px 32px;
    max-width: 820px;
    margin: 0 auto;
    font-size: 16px;
    line-height: 1.8;
    color: var(--glass-text-primary);

    :deep(h1) {
      font-size: 26px;
      margin: 32px 0 16px;
      padding-bottom: 10px;
      border-bottom: 2px solid var(--glass-stroke-base);
      color: var(--glass-text-primary);
      font-weight: 700;
    }

    :deep(h2) {
      font-size: 22px;
      margin: 28px 0 14px;
      padding-bottom: 8px;
      border-bottom: 2px solid var(--glass-stroke-soft);
      color: var(--glass-text-primary);
      font-weight: 600;
    }

    :deep(h3) {
      font-size: 19px;
      margin: 22px 0 12px;
      color: var(--glass-text-secondary);
      font-weight: 600;
    }

    :deep(h4) {
      font-size: 17px;
      margin: 18px 0 10px;
      color: var(--glass-text-secondary);
      font-weight: 600;
    }

    :deep(p) {
      margin: 14px 0;
      text-align: justify;
    }

    :deep(ul), :deep(ol) {
      margin: 14px 0;
      padding-left: 24px;
      li { margin: 6px 0; }
    }

    :deep(code) {
      background: var(--el-fill-color-light);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 14px;
      color: var(--glass-text-primary);
    }

    :deep(pre) {
      background: var(--el-fill-color-light);
      color: var(--glass-text-primary);
      padding: 16px;
      border-radius: var(--glass-radius-sm);
      overflow-x: auto;
      margin: 14px 0;

      code {
        background: none;
        padding: 0;
        color: inherit;
      }
    }

    :deep(blockquote) {
      border-left: 4px solid var(--el-color-primary);
      margin: 14px 0;
      padding: 12px 16px;
      color: var(--glass-text-secondary);
      background: var(--el-color-primary-light-9);
      border-radius: 4px;
    }

    :deep(img) {
      max-width: 100%;
      height: auto;
      display: block;
      margin: 12px auto;
    }

    :deep(table) {
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0;

      th, td {
        border: 1px solid var(--glass-stroke-base);
        padding: 8px 12px;
        text-align: left;
      }

      th {
        background: var(--el-fill-color-light);
        font-weight: 600;
      }
    }

    :deep(a) {
      color: var(--el-color-primary);
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }
}

// ---- 响应式 ----
@media (max-width: 768px) {
  .article-list-panel {
    width: 200px;
  }

  .article-content {
    padding: 20px 16px !important;
    font-size: 15px;
  }
}
</style>
