<template>
  <div class="data-collection-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon"><DataAnalysis /></el-icon>
        <div>
          <h2>数据采集</h2>
          <p class="header-desc">一键采集自选股实时行情、技术指标和新闻数据，支持导出 Markdown 分析文件</p>
        </div>
      </div>
      <div class="header-right">
        <el-button
          type="primary"
          size="large"
          :icon="Download"
          :disabled="!stockData.length"
          @click="exportMarkdown"
        >
          导出 Markdown
        </el-button>
      </div>
    </div>

    <!-- 采集配置 -->
    <el-card class="config-card" shadow="never">
      <div class="config-bar">
        <div class="config-left">
          <span class="config-label">采集范围：</span>
          <el-radio-group v-model="collectScope" :disabled="loading">
            <el-radio-button value="favorites">自选股</el-radio-button>
            <el-radio-button value="custom">自定义股票</el-radio-button>
          </el-radio-group>

          <el-input
            v-if="collectScope === 'custom'"
            v-model="customCodes"
            placeholder="输入股票代码，逗号分隔（如 000001,600036）"
            style="width: 360px; margin-left: 12px"
            :disabled="loading"
            clearable
          />
        </div>

        <div class="config-right">
          <el-tooltip content="是否采集每只股票的最新新闻" placement="top">
            <el-switch v-model="includeNews" active-text="新闻" :disabled="loading" />
          </el-tooltip>
          <el-input-number
            v-if="includeNews"
            v-model="newsLimit"
            :min="1"
            :max="10"
            size="small"
            style="margin-left: 12px; width: 90px"
            :disabled="loading"
          />
          <span v-if="includeNews" class="config-hint">条/股</span>

          <el-input-number
            v-model="histDays"
            :min="60"
            :max="1000"
            :step="60"
            size="small"
            style="margin-left: 16px; width: 110px"
            :disabled="loading"
          />
          <span class="config-hint">天K线</span>
        </div>

        <el-button
          type="primary"
          size="large"
          :icon="Refresh"
          :loading="loading"
          @click="handleCollect"
          style="margin-left: 20px"
        >
          {{ loading ? '采集中...' : '一键采集' }}
        </el-button>
      </div>
    </el-card>

    <!-- 数据展示 -->
    <el-card v-loading="loading" shadow="never" class="data-card">
      <template v-if="!stockData.length && !newsData.length && !loading">
        <el-empty description="点击「一键采集」开始获取数据" :image-size="120" />
      </template>

      <template v-else>
        <!-- 采集摘要 -->
        <div class="collect-summary" v-if="collectedAt">
          <el-tag type="info" effect="plain">
            <el-icon><Clock /></el-icon>
            采集时间：{{ collectedAt }}
          </el-tag>
          <el-tag type="success" effect="plain">股票 {{ stockData.length }} 只</el-tag>
          <el-tag type="warning" effect="plain" v-if="newsData.length">新闻 {{ newsData.length }} 条</el-tag>
          <el-tag type="danger" effect="plain" v-if="warnings.length">警告 {{ warnings.length }} 条</el-tag>
        </div>

        <!-- 警告信息 -->
        <el-alert
          v-if="warnings.length"
          class="warnings-alert"
          type="warning"
          :closable="false"
          show-icon
        >
          <template #title>
            <div v-for="(w, i) in warnings" :key="i" class="warning-line">⚠️ {{ w }}</div>
          </template>
        </el-alert>

        <!-- Tab 切换 -->
        <el-tabs v-model="activeTab" class="data-tabs">
          <!-- 股票行情 + 技术指标 -->
          <el-tab-pane name="stocks">
            <template #label>
              <span>📈 行情指标 ({{ stockData.length }})</span>
            </template>

            <el-table
              :data="stockData"
              stripe
              border
              size="small"
              :default-sort="{ prop: 'change_percent', order: 'descending' }"
              style="width: 100%"
              :max-height="tableHeight"
            >
              <el-table-column prop="code" label="代码" width="80" fixed />
              <el-table-column prop="name" label="名称" width="90" fixed show-overflow-tooltip />
              <el-table-column prop="market_board" label="板块" width="70" />

              <el-table-column label="实时行情" align="center">
                <el-table-column prop="price" label="最新价" width="75" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.price, 2) }}</template>
                </el-table-column>
                <el-table-column prop="change_percent" label="涨跌幅%" width="85" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.change_percent)">{{ fmtNum(row.change_percent, 2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="volume_ratio" label="量比" width="70" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.volume_ratio, 2) }}</template>
                </el-table-column>
                <el-table-column prop="turnover_rate" label="换手率%" width="85" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.turnover_rate, 2) }}</template>
                </el-table-column>
                <el-table-column prop="amount_yi" label="成交额亿" width="90" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.amount_yi, 2) }}</template>
                </el-table-column>
                <el-table-column prop="total_mv_yi" label="总市值亿" width="95" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.total_mv_yi, 0) }}</template>
                </el-table-column>
                <el-table-column prop="pe" label="PE" width="65" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.pe, 1) }}</template>
                </el-table-column>
                <el-table-column prop="pb" label="PB" width="65" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.pb, 2) }}</template>
                </el-table-column>
              </el-table-column>

              <el-table-column label="技术指标" align="center">
                <el-table-column prop="ma5" label="MA5" width="70" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.ma5, 2) }}</template>
                </el-table-column>
                <el-table-column prop="ma20" label="MA20" width="75" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.ma20, 2) }}</template>
                </el-table-column>
                <el-table-column prop="ma60" label="MA60" width="75" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.ma60, 2) }}</template>
                </el-table-column>
                <el-table-column prop="ma20_bias" label="MA20乖离%" width="100" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.ma20_bias)">{{ fmtNum(row.ma20_bias, 2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="rsi14" label="RSI14" width="70" sortable align="right">
                  <template #default="{ row }">
                    <span :class="rsiClass(row.rsi14)">{{ fmtNum(row.rsi14, 1) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="macd_hist" label="MACD柱" width="80" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.macd_hist)">{{ fmtNum(row.macd_hist, 2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="boll_position" label="布林位置" width="85" sortable align="right">
                  <template #default="{ row }">{{ fmtNum(row.boll_position, 2) }}</template>
                </el-table-column>
              </el-table-column>

              <el-table-column label="涨跌幅统计" align="center">
                <el-table-column prop="pct_5d" label="5日%" width="70" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.pct_5d)">{{ fmtNum(row.pct_5d, 2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="pct_20d" label="20日%" width="70" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.pct_20d)">{{ fmtNum(row.pct_20d, 2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="pct_60d" label="60日%" width="70" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.pct_60d)">{{ fmtNum(row.pct_60d, 2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="pct_60d_drawdown" label="60日回撤%" width="100" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.pct_60d_drawdown)">{{ fmtNum(row.pct_60d_drawdown, 2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="pct_ytd" label="年初至今%" width="95" sortable align="right">
                  <template #default="{ row }">
                    <span :class="pctClass(row.pct_ytd)">{{ fmtNum(row.pct_ytd, 2) }}</span>
                  </template>
                </el-table-column>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 新闻列表 -->
          <el-tab-pane name="news" v-if="newsData.length">
            <template #label>
              <span>📰 新闻 ({{ newsData.length }})</span>
            </template>

            <el-table
              :data="newsData"
              stripe
              border
              size="small"
              style="width: 100%"
              :max-height="tableHeight"
            >
              <el-table-column prop="code" label="代码" width="80" fixed />
              <el-table-column label="新闻标题" min-width="400" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-link
                    v-if="row.url"
                    :href="row.url"
                    target="_blank"
                    type="primary"
                    :underline="false"
                  >{{ row.title }}</el-link>
                  <span v-else>{{ row.title }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="source" label="来源" width="120" show-overflow-tooltip />
              <el-table-column prop="publish_time" label="发布时间" width="170">
                <template #default="{ row }">{{ formatTime(row.publish_time) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Refresh, Download, Clock } from '@element-plus/icons-vue'
import { dataCollectionApi, type StockDataItem, type NewsDataItem } from '@/api/dataCollection'
import { formatDateTime } from '@/utils/datetime'
import { showError } from '@/utils/message'

// ---- 采集配置 ----
const collectScope = ref<'favorites' | 'custom'>('favorites')
const customCodes = ref('')
const includeNews = ref(true)
const newsLimit = ref(3)
const histDays = ref(420)

// ---- 采集状态 ----
const loading = ref(false)
const stockData = ref<StockDataItem[]>([])
const newsData = ref<NewsDataItem[]>([])
const warnings = ref<string[]>([])
const collectedAt = ref('')
const activeTab = ref('stocks')

const tableHeight = computed(() => 'calc(100vh - 380px)')

// ---- 一键采集 ----
const handleCollect = async () => {
  let codes: string[] = []

  if (collectScope.value === 'custom') {
    codes = customCodes.value
      .split(/[,，\s]+/)
      .map(c => c.trim())
      .filter(Boolean)
    if (!codes.length) {
      ElMessage.warning('请输入至少一个股票代码')
      return
    }
  }

  loading.value = true
  stockData.value = []
  newsData.value = []
  warnings.value = []

  try {
    const res = await dataCollectionApi.collect({
      stock_codes: codes,
      include_news: includeNews.value,
      news_limit: newsLimit.value,
      hist_days: histDays.value,
    })

    const data = (res as any)?.data?.data || (res as any)?.data || res
    const payload = data?.data || data

    stockData.value = payload?.stocks || []
    newsData.value = payload?.news || []
    warnings.value = payload?.warnings || []
    collectedAt.value = payload?.collected_at || ''

    activeTab.value = 'stocks'

    if (stockData.value.length) {
      ElMessage.success(`采集完成：${stockData.value.length} 只股票${newsData.value.length ? `，${newsData.value.length} 条新闻` : ''}`)
    } else {
      ElMessage.warning('采集完成，但未获取到股票数据')
    }
  } catch (error: any) {
    showError(error?.message || '采集失败')
  } finally {
    loading.value = false
  }
}

// ---- 导出 Markdown ----
const exportMarkdown = () => {
  if (!stockData.value.length) return

  const ts = collectedAt.value || new Date().toLocaleString('zh-CN')
  const parts: string[] = []

  parts.push('# 自选股实时行情评分')
  parts.push('')
  parts.push(`> 数据获取时间：${ts}`)
  parts.push('')
  parts.push('> 说明：本文件是数据采集文件，不做最终投资评分。系统只负责获取行情、技术指标和新闻原始数据；最终评分请交给 AI 分析。')
  parts.push('')

  // 分析提示词
  parts.push('## 一、给 AI 的分析提示词')
  parts.push('')
  parts.push(PROMPT_TEXT)
  parts.push('')

  // 股票行情表
  parts.push('## 二、股票实时行情 + 技术指标原始数据')
  parts.push('')
  parts.push('| 代码 | 名称 | 板块 | 最新价 | 涨跌幅% | 量比 | 换手率% | 成交额亿 | 总市值亿 | PE | PB | MA5 | MA20 | MA60 | MA20乖离% | RSI14 | MACD柱 | 布林位置 | 5日% | 20日% | 60日% | 60日回撤% | 年初至今% |')
  parts.push('|------|------|------|--------|---------|------|---------|---------|---------|-----|-----|-----|-------|-------|----------|-------|--------|----------|------|-------|-------|----------|----------|')

  for (const s of stockData.value) {
    parts.push([
      s.code, s.name, s.market_board,
      fmtNum(s.price, 2), fmtNum(s.change_percent, 2),
      fmtNum(s.volume_ratio, 2), fmtNum(s.turnover_rate, 2),
      fmtNum(s.amount_yi, 2), fmtNum(s.total_mv_yi, 0),
      fmtNum(s.pe, 1), fmtNum(s.pb, 2),
      fmtNum(s.ma5, 2), fmtNum(s.ma20, 2), fmtNum(s.ma60, 2),
      fmtNum(s.ma20_bias, 2), fmtNum(s.rsi14, 1), fmtNum(s.macd_hist, 2),
      fmtNum(s.boll_position, 2),
      fmtNum(s.pct_5d, 2), fmtNum(s.pct_20d, 2), fmtNum(s.pct_60d, 2),
      fmtNum(s.pct_60d_drawdown, 2), fmtNum(s.pct_ytd, 2),
    ].join(' | '))
  }
  parts.push('')

  // 新闻
  if (newsData.value.length) {
    parts.push('## 三、新闻原始数据')
    parts.push('')
    parts.push('| 代码 | 新闻标题 | 来源 | 发布时间 |')
    parts.push('|------|----------|------|----------|')
    for (const n of newsData.value) {
      parts.push([n.code, n.title, n.source, formatTime(n.publish_time)].join(' | '))
    }
    parts.push('')
  }

  // 警告
  if (warnings.value.length) {
    parts.push('## 四、数据获取警告')
    parts.push('')
    for (const w of warnings.value) {
      parts.push(`- ${w}`)
    }
    parts.push('')
  }

  // 下载
  const blob = new Blob([parts.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `自选股数据采集_${new Date().toISOString().slice(0, 10)}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)

  ElMessage.success('Markdown 文件已导出')
}

// ---- 格式化工具 ----
const fmtNum = (val: any, decimals = 2): string => {
  if (val === null || val === undefined || val === '' || isNaN(val)) return '-'
  return Number(val).toFixed(decimals)
}

const formatTime = (t: string): string => {
  if (!t) return '-'
  return formatDateTime(t)
}

const pctClass = (val: any): string => {
  if (val === null || val === undefined || isNaN(val)) return ''
  if (val > 0) return 'text-up'
  if (val < 0) return 'text-down'
  return ''
}

const rsiClass = (val: any): string => {
  if (val === null || val === undefined || isNaN(val)) return ''
  if (val >= 80) return 'text-overheat'
  if (val >= 70) return 'text-hot'
  return ''
}

// ---- 分析提示词（从 Python 脚本搬过来） ----
const PROMPT_TEXT = `请你根据下面这批 A 股自选股的实时数据，帮我做一次"T+1 超短线轮动策略"的选股分析。

我的真实交易策略如下：

1. 我通常会在早上 10:00 左右卖出昨日持仓。
2. 我会在中午到下午收集行情、新闻和技术指标数据。
3. 我会在下午 14:00 左右买入新的股票。
4. 我的持仓周期很短，通常是今天 14:00 左右买入，第二天 10:00 左右卖出。
5. 我计划同时持有 2 只股票，每只股票约半仓。
6. 这 2 只股票必须尽量属于不同板块或不同细分主题，不能都集中在同一个方向。
7. 这 2 个板块都必须是当天热门板块，或者至少有明显资金参与。
8. 如果当天只有一个板块明显强势，另一个板块没有合适股票，可以建议只买一只、另一半仓位空着，不要为了凑两只而买弱板块。
9. 这不是长线投资，也不是普通波段，不要只看公司长期好坏，要重点判断：今天 14:00 买进去，明天 10:00 前后是否更可能有冲高溢价。

请按以下逻辑分析：

一、先判断今日市场资金主线
二、再判断个股是否适合今天 14:00 买入、明天 10:00 卖出
三、两只股票组合选择规则（必须来自不同热门板块）
四、14:00 买入确认条件
五、放弃买入条件
六、把股票分成四类（第一半仓候选 / 第二半仓候选 / 只观察不买 / 不建议买入）
七、最终两只股票组合建议
八、仓位要求
九、次日 10:00 卖出计划
十、输出格式（含评分表格）

评分标准：90分以上非常适合T+1，80-89优先候选，70-79可观察，60-69风险偏高，60分以下不建议买入。`
</script>

<style scoped lang="scss">
.data-collection-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .header-icon {
      font-size: 32px;
      color: var(--el-color-primary);
    }

    h2 {
      margin: 0;
      font-size: 22px;
      font-weight: 600;
    }

    .header-desc {
      margin: 4px 0 0;
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }
  }
}

.config-card {
  margin-bottom: 16px;

  :deep(.el-card__body) {
    padding: 16px 20px;
  }

  .config-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;

    .config-left {
      display: flex;
      align-items: center;
    }

    .config-right {
      display: flex;
      align-items: center;
      margin-left: 20px;
    }

    .config-label {
      font-size: 14px;
      color: var(--el-text-color-regular);
      margin-right: 8px;
    }

    .config-hint {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-left: 4px;
    }
  }
}

.data-card {
  :deep(.el-card__body) {
    padding: 16px 20px;
  }
}

.collect-summary {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;

  .el-tag {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.warnings-alert {
  margin-bottom: 12px;

  .warning-line {
    font-size: 12px;
    line-height: 1.8;
  }
}

.data-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 12px;
  }
}

/* 涨跌颜色 */
:deep(.text-up) {
  color: #f56c6c;
  font-weight: 600;
}

:deep(.text-down) {
  color: #67c23a;
  font-weight: 600;
}

:deep(.text-hot) {
  color: #e6a23c;
  font-weight: 600;
}

:deep(.text-overheat) {
  color: #f56c6c;
  font-weight: 700;
}
</style>
