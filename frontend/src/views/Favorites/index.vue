<template>
  <div class="favorites">
    <!-- 操作栏：按钮在左，搜索在右 -->
    <el-card class="action-card fade-in-up" shadow="never">
      <div class="action-bar">
        <div class="action-buttons">
          <el-button @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button type="warning" @click="loadTopGainers" :loading="topGainersLoading">
            <el-icon><TrendCharts /></el-icon>
            热门股票
          </el-button>
          <el-button type="success" @click="showBatchImportDialog">
            <el-icon><Upload /></el-icon>
            批量导入
          </el-button>
        </div>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索股票代码或名称"
          clearable
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </el-card>

    <!-- 自选股列表 -->
    <el-card class="favorites-list-card" shadow="never">
      <el-table
        :data="filteredFavorites"
        v-loading="loading"
        style="width: 100%"
        :row-class-name="({ row }) => getIndustryClass(row.industry)"
        @row-contextmenu="handleRowContextMenu"
      >
        <el-table-column type="index" label="#" width="55" align="center" />
        <el-table-column prop="stock_code" label="股票代码" min-width="120">
          <template #default="{ row }">
            <el-link type="primary" @click="viewStockDetail(row)">
              {{ row.stock_code }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column prop="stock_name" label="股票名称" min-width="150" />

        <el-table-column prop="industry" label="行业" min-width="150">
          <template #default="{ row }">
            <el-tag
              v-if="row.industry && row.industry !== '-'"
              size="small"
              effect="plain"
              type="info"
            >
              {{ row.industry }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="current_price" label="当前价格" min-width="100">
          <template #default="{ row }">
            <span v-if="row.current_price !== null && row.current_price !== undefined">¥{{ formatPrice(row.current_price) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="change_percent" label="涨跌幅" min-width="100">
          <template #default="{ row }">
            <span
              v-if="row.change_percent !== null && row.change_percent !== undefined"
              :class="getChangeClass(row.change_percent)"
            >
              {{ formatPercent(row.change_percent) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="turnover_rate" label="换手率" min-width="100">
          <template #default="{ row }">
            <span v-if="row.turnover_rate !== null && row.turnover_rate !== undefined">
              {{ Number(row.turnover_rate).toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="volume_ratio" label="量比" min-width="90">
          <template #default="{ row }">
            <span
              v-if="row.volume_ratio !== null && row.volume_ratio !== undefined"
              :class="{ 'text-danger': row.volume_ratio >= 2, 'text-warning': row.volume_ratio >= 1 && row.volume_ratio < 2 }"
            >
              {{ Number(row.volume_ratio).toFixed(2) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column label="今日报告" width="110" align="center">
          <template #default="{ row }">
            <el-badge
              :is-dot="hasReportToday(row.stock_code)"
              :hidden="!hasReportToday(row.stock_code)"
              class="report-badge"
            >
              <el-button type="primary" link size="small" @click="openReportDrawer(row)">
                <el-icon><Document /></el-icon>
                查看
              </el-button>
            </el-badge>
          </template>
        </el-table-column>
      </el-table>

      <!-- 右键菜单 -->
      <el-dropdown
        ref="contextMenuRef"
        trigger="contextmenu"
        placement="bottom-start"
        :visible="contextMenuVisible"
        @visible-change="(v: boolean) => contextMenuVisible = v"
      >
        <template #default><span /></template>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="editFavorite(contextMenuRow)">编辑</el-dropdown-item>
            <el-dropdown-item @click="analyzeFavorite(contextMenuRow)">分析</el-dropdown-item>
            <el-dropdown-item @click="openReportDrawer(contextMenuRow)">今日报告</el-dropdown-item>
            <el-dropdown-item @click="removeFavorite(contextMenuRow)" divided>移除</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <!-- 空状态 -->
      <div v-if="!loading && favorites.length === 0" class="empty-state">
        <el-empty description="暂无自选股">
          <el-button type="primary" @click="showBatchImportDialog">
            批量导入自选股
          </el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 分析报告抽屉 -->
    <StockReportDrawer
      v-model="reportDrawerVisible"
      :stock-code="reportDrawerStockCode"
      :stock-name="reportDrawerStockName"
      @generated="loadReportBadges"
    />

    <!-- 编辑自选股对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑自选股"
      width="520px"
    >
      <el-form :model="editForm" ref="editFormRef" label-width="100px">
        <el-form-item label="股票">
          <div>{{ editForm.stock_code }}｜{{ editForm.stock_name }}<span v-if="editForm.industry && editForm.industry !== '-'" style="color: var(--glass-text-tertiary); margin-left: 8px;">{{ editForm.industry }}</span></div>
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleUpdateFavorite">保存</el-button>
      </template>
    </el-dialog>

    <!-- 热门股票（涨幅榜）对话框 -->
    <el-dialog
      v-model="topGainersDialogVisible"
      title="热门股票 · 涨幅榜 Top 20"
      width="720px"
      :close-on-click-modal="false"
    >
      <div v-if="topGainersLoading" v-loading="true" style="min-height: 200px"></div>
      <div v-else>
        <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
          <el-checkbox v-model="topGainersSelectAll" :indeterminate="topGainersIndeterminate" @change="onSelectAllGainers">
            全选
          </el-checkbox>
          <span style="color: var(--glass-text-tertiary); font-size: 12px;">
            已选 {{ topGainersSelected.length }} 只，数据来自实时行情
          </span>
        </div>
        <el-table :data="topGainersList" max-height="400" size="small" @selection-change="onGainersSelectionChange">
          <el-table-column type="selection" width="40" :selectable="(row: any) => !isAlreadyFavorite(row.stock_code)" />
          <el-table-column label="代码" prop="stock_code" width="80" />
          <el-table-column label="名称" prop="stock_name" min-width="100" />
          <el-table-column label="最新价" width="80">
            <template #default="{ row }">{{ row.current_price != null ? row.current_price.toFixed(2) : '-' }}</template>
          </el-table-column>
          <el-table-column label="涨跌幅" width="80">
            <template #default="{ row }">
              <span :style="{ color: (row.change_percent || 0) > 0 ? 'var(--el-color-danger)' : 'var(--el-color-success)' }">
                {{ row.change_percent != null ? (row.change_percent > 0 ? '+' : '') + row.change_percent.toFixed(2) + '%' : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="换手率" width="80">
            <template #default="{ row }">{{ row.turnover_rate != null ? row.turnover_rate.toFixed(2) + '%' : '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="70">
            <template #default="{ row }">
              <el-tag v-if="isAlreadyFavorite(row.stock_code)" type="info" size="small">已加</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="topGainersDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addSelectedGainers" :loading="addingGainers" :disabled="topGainersSelected.length === 0">
          加入自选（{{ topGainersSelected.length }}）
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="batchImportDialogVisible"
      title="批量导入自选股"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 16px;"
      >
        每行输入一个股票名称或代码，系统自动识别 A 股个股并添加到自选股。ETF、指数、美股、港股等非 A 股品种会自动跳过。
      </el-alert>

      <el-input
        v-model="batchImportText"
        type="textarea"
        :rows="12"
        placeholder="每行一个股票名称或代码，例如：&#10;中际旭创&#10;兆易创新&#10;宁德时代&#10;000001"
        :disabled="batchImportLoading"
      />

      <!-- 导入进度 -->
      <div v-if="batchImportLoading" style="margin-top: 16px;">
        <el-progress :percentage="batchImportProgress" :format="() => batchImportStatusText" />
      </div>

      <!-- 导入结果 -->
      <div v-if="batchImportResult" style="margin-top: 16px;">
        <el-alert
          :type="batchImportResult.failed.length > 0 ? 'warning' : 'success'"
          :closable="false"
          style="margin-bottom: 12px;"
        >
          <div>
            ✅ 成功添加 <strong>{{ batchImportResult.added }}</strong> 只，
            ⏭️ 已存在 <strong>{{ batchImportResult.existed }}</strong> 只，
            ❌ 未识别 <strong>{{ batchImportResult.failed.length }}</strong> 只
          </div>
        </el-alert>
        <div v-if="batchImportResult.failed.length > 0" style="font-size: 13px; color: var(--glass-text-tertiary);">
          未识别的行（非 A 股个股或未找到匹配）：
          <el-tag
            v-for="item in batchImportResult.failed"
            :key="item"
            size="small"
            type="info"
            style="margin: 2px;"
          >
            {{ item }}
          </el-tag>
        </div>
      </div>

      <template #footer>
        <el-button @click="batchImportDialogVisible = false">关闭</el-button>
        <el-button
          type="primary"
          @click="handleBatchImport"
          :loading="batchImportLoading"
          :disabled="!batchImportText.trim()"
        >
          开始导入
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getIndustryClass } from '@/utils/industryColor'
import {
  Search,
  Refresh,
  Upload,
  Document,
  TrendCharts
} from '@element-plus/icons-vue'
import { favoritesApi, favoriteReportsApi, topGainersApi } from '@/api/favorites'
import type { TopGainer } from '@/api/favorites'
import { normalizeMarketForAnalysis } from '@/utils/market'
import StockReportDrawer from './components/StockReportDrawer.vue'

import type { FavoriteItem } from '@/api/favorites'
import { showError } from '@/utils/message'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const favorites = ref<FavoriteItem[]>([])

// 行业优先级映射：数字越小排越前；未列出的行业统一归到 999（末尾），'-' / 空值归到 1000（最末尾）
// 行业值由 LLM 动态生成（细分赛道），这里按 A 股主赛道重要性固定排序，无需手动操作
const INDUSTRY_ORDER: Record<string, number> = {
  // 核心科技
  '半导体': 1, '半导体设备': 1, '芯片': 1, '集成电路': 1, '光刻胶': 1, 'EDA': 1,
  '消费电子': 2, '电子元件': 2, 'PCB': 2, '面板': 2, '光学光电子': 2,
  '人工智能': 3, 'AI': 3, '算力': 3, '数据中心': 3, '云计算': 3,
  '通信设备': 4, '通信服务': 4, '5G': 4,
  '软件': 5, '软件开发': 5, 'IT服务': 5, '计算机设备': 5,
  // 新能源
  '锂电池': 10, '电池': 10, '新能源': 10, '光伏': 11, '风电': 12, '储能': 13,
  '新能源汽车': 14, '汽车零部件': 15, '汽车': 15,
  // 医药生物
  '医药生物': 20, '医疗器械': 20, '化学制药': 21, '生物制品': 22, '中药': 23, '医疗服务': 24,
  // 高端制造
  '军工': 30, '国防军工': 30, '航空航天': 30,
  '机械设备': 31, '工业母机': 31, '机器人': 32, '自动化设备': 32,
  '电力设备': 33, '电网': 33,
  // 消费
  '食品饮料': 40, '白酒': 40, '家电': 41, '纺织服装': 42, '商贸零售': 43, '社会服务': 44, '美容护理': 45,
  '传媒': 46, '游戏': 46, '教育': 47,
  // 周期/材料
  '化工': 50, '化学原料': 50, '化学制品': 50,
  '钢铁': 51, '有色金属': 52, '小金属': 52, '贵金属': 52,
  '建筑材料': 53, '建筑装饰': 54, '房地产': 55,
  '煤炭': 56, '石油石化': 57, '环保': 58,
  // 金融
  '银行': 60, '证券': 61, '保险': 62, '多元金融': 63,
  // 基础设施
  '交通运输': 70, '公用事业': 71, '农林牧渔': 72,
}

// 取行业优先级：未命中映射返回 999（末尾），'-' 或空值返回 1000（最末尾）
const getIndustryOrder = (industry: string | undefined | null): number => {
  if (!industry || industry === '-') return 1000
  return INDUSTRY_ORDER[industry] ?? 999
}

const searchKeyword = ref('')

// ==================== 分析报告抽屉 ====================
const reportDrawerVisible = ref(false)
const reportDrawerStockCode = ref('')
const reportDrawerStockName = ref('')
// 当日报告徽标缓存：{ [stock_code]: { has_daily, has_realtime } }
const reportBadges = ref<Record<string, { has_daily: boolean; has_realtime: boolean }>>({})

const openReportDrawer = (row: any) => {
  if (!row) return
  reportDrawerStockCode.value = row.stock_code || ''
  reportDrawerStockName.value = row.stock_name || ''
  reportDrawerVisible.value = true
}

const hasReportToday = (stockCode?: string): boolean => {
  if (!stockCode) return false
  const b = reportBadges.value[stockCode]
  return !!(b && (b.has_daily || b.has_realtime))
}

// 加载全部自选股的当日报告徽标（用于红点提示）
const loadReportBadges = async () => {
  const codes = favorites.value
    .map(f => f.stock_code)
    .filter((c): c is string => !!c)
  if (codes.length === 0) return
  try {
    const results = await Promise.all(
      codes.map(async (code) => {
        try {
          const resp = await favoriteReportsApi.hasToday(code)
          const data = (resp as any)?.data
          return [code, data || { has_daily: false, has_realtime: false }] as const
        } catch {
          return [code, { has_daily: false, has_realtime: false }] as const
        }
      })
    )
    const map: Record<string, { has_daily: boolean; has_realtime: boolean }> = {}
    for (const [code, info] of results) {
      map[code] = info
    }
    reportBadges.value = map
  } catch (e) {
    console.warn('加载报告徽标失败', e)
  }
}

// 右键菜单
const contextMenuRef = ref()
const contextMenuVisible = ref(false)
const contextMenuRow = ref<FavoriteItem | null>(null)

// 右键行时弹出菜单（阻止浏览器默认右键菜单）
const handleRowContextMenu = (row: FavoriteItem, _column: any, event: MouseEvent) => {
  event.preventDefault()
  contextMenuRow.value = row
  contextMenuVisible.value = true
}

// ==================== 热门股票（涨幅榜）====================
const topGainersDialogVisible = ref(false)
const topGainersLoading = ref(false)
const topGainersList = ref<TopGainer[]>([])
const topGainersSelected = ref<TopGainer[]>([])
const addingGainers = ref(false)

const topGainersSelectAll = computed({
  get: () => {
    const selectable = topGainersList.value.filter(e => !isAlreadyFavorite(e.stock_code))
    return selectable.length > 0 && selectable.every(e => topGainersSelected.value.some(s => s.stock_code === e.stock_code))
  },
  set: () => {},
})
const topGainersIndeterminate = computed(() => {
  const selectable = topGainersList.value.filter(e => !isAlreadyFavorite(e.stock_code))
  const selCount = topGainersSelected.value.filter(s => !isAlreadyFavorite(s.stock_code)).length
  return selCount > 0 && selCount < selectable.length
})

const isAlreadyFavorite = (code: string) => favorites.value.some(f => f.stock_code === code)

const loadTopGainers = async () => {
  topGainersDialogVisible.value = true
  topGainersLoading.value = true
  topGainersSelected.value = []
  try {
    const res = await topGainersApi.list(20)
    topGainersList.value = ((res as any)?.data || []) as TopGainer[]
  } catch (e: any) {
    ElMessage.error(e?.message || '加载热门股票失败')
    topGainersList.value = []
  } finally {
    topGainersLoading.value = false
  }
}

const onSelectAllGainers = (val: any) => {
  if (val) {
    topGainersSelected.value = topGainersList.value.filter(e => !isAlreadyFavorite(e.stock_code))
  } else {
    topGainersSelected.value = []
  }
}
const onGainersSelectionChange = (sel: TopGainer[]) => { topGainersSelected.value = sel }

const addSelectedGainers = async () => {
  if (topGainersSelected.value.length === 0) return
  addingGainers.value = true
  let ok = 0
  let fail = 0
  for (const g of topGainersSelected.value) {
    try {
      await favoritesApi.add({ symbol: g.stock_code, stock_name: g.stock_name, market: 'A股' })
      ok++
    } catch {
      fail++
    }
  }
  addingGainers.value = false
  if (ok > 0) {
    ElMessage.success(`成功加入 ${ok} 只自选${fail > 0 ? `，${fail} 只失败` : ''}`)
    topGainersDialogVisible.value = false
    await loadFavorites()
  } else {
    ElMessage.error('加入失败，可能已存在')
  }
}

// 批量导入对话框
const batchImportDialogVisible = ref(false)
const batchImportLoading = ref(false)
const batchImportText = ref('')
const batchImportProgress = ref(0)
const batchImportStatusText = ref('')
const batchImportResult = ref<{
  added: number
  existed: number
  failed: string[]
} | null>(null)

// 编辑对话框
const editDialogVisible = ref(false)
const editLoading = ref(false)
const editFormRef = ref()
const editForm = ref({
  stock_code: '',
  stock_name: '',
  market: 'A股',
  industry: '-',
  notes: ''
})

// 计算属性
const filteredFavorites = computed<FavoriteItem[]>(() => {
  let result: FavoriteItem[] = favorites.value

  // 关键词搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter((item: FavoriteItem) =>
      (item.stock_code || '').toLowerCase().includes(keyword) ||
      (item.stock_name || '').toLowerCase().includes(keyword)
    )
  }

  // 按行业优先级固定排序（同行业再按股票代码排，保证稳定）
  return [...result].sort((a, b) => {
    const ia = a.industry || '-'
    const ib = b.industry || '-'
    const orderDiff = getIndustryOrder(ia) - getIndustryOrder(ib)
    if (orderDiff !== 0) return orderDiff
    if (ia !== ib) return ia.localeCompare(ib, 'zh-CN')
    return (a.stock_code || '').localeCompare(b.stock_code || '')
  })
})

// 方法
const loadFavorites = async () => {
  loading.value = true
  try {
    const res = await favoritesApi.list()
    favorites.value = ((res as any)?.data || []) as FavoriteItem[]
    // 启动每分钟自动刷新（行情入库是6分钟一次，60秒刷新足够看到更新）
    startAutoRefresh()
  } catch (error: any) {
    console.error('加载自选股失败:', error)
    showError(error.message || '加载自选股失败')
  } finally {
    loading.value = false
  }
}

// 每分钟自动刷新整表（静默，不显示 loading、不弹提示）
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null
const AUTO_REFRESH_INTERVAL = 60000  // 60秒

const startAutoRefresh = () => {
  stopAutoRefresh()
  autoRefreshTimer = setInterval(async () => {
    try {
      const res = await favoritesApi.list()
      const newList = ((res as any)?.data || []) as FavoriteItem[]
      favorites.value = newList
    } catch (e) {
      // 静默忽略刷新失败
    }
  }, AUTO_REFRESH_INTERVAL)
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

const refreshData = () => {
  loadFavorites()
}

// ========== 批量导入 ==========

const showBatchImportDialog = () => {
  batchImportText.value = ''
  batchImportResult.value = null
  batchImportProgress.value = 0
  batchImportStatusText.value = ''
  batchImportDialogVisible.value = true
}

const handleBatchImport = async () => {
  // 按换行拆分，去空行、去重、去首尾空格
  const lines = batchImportText.value
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0)
  // 去重（保留顺序）
  const uniqueLines = [...new Set(lines)]

  if (uniqueLines.length === 0) {
    ElMessage.warning('请输入至少一行股票名称或代码')
    return
  }

  batchImportLoading.value = true
  batchImportResult.value = null
  batchImportProgress.value = 0

  let added = 0
  let existed = 0
  const failed: string[] = []

  for (let i = 0; i < uniqueLines.length; i++) {
    const keyword = uniqueLines[i]
    batchImportStatusText.value = `正在处理 ${i + 1}/${uniqueLines.length}：${keyword}`
    batchImportProgress.value = Math.round(((i + 1) / uniqueLines.length) * 100)

    try {
      // 1. 搜索 A 股股票（stock_basic_info 集合只含 A 股个股，ETF/指数天然被过滤）
      const searchRes = await favoritesApi.searchStock(keyword) as any
      if (!searchRes?.success || !searchRes?.data || searchRes.data.length === 0) {
        failed.push(keyword)
        continue
      }

      const stock = searchRes.data[0]
      const stockCode = stock.symbol || stock.code
      const stockName = stock.name

      if (!stockCode || !stockName) {
        failed.push(keyword)
        continue
      }

      // 2. 添加到自选股
      try {
        const addRes = await favoritesApi.add({
          stock_code: stockCode,
          stock_name: stockName,
          market: 'A股',
        } as any) as any

        if (addRes?.success) {
          added++
        } else {
          // 后端返回 success=false 通常是已存在
          existed++
        }
      } catch (addError: any) {
        // HTTP 400 = 已存在，不算错误
        const status = addError?.response?.status
        if (status === 400) {
          existed++
        } else {
          console.error(`添加 ${keyword} 失败:`, addError)
          failed.push(keyword)
        }
      }
    } catch (error) {
      console.error(`搜索 ${keyword} 失败:`, error)
      failed.push(keyword)
    }
  }

  batchImportResult.value = { added, existed, failed }
  batchImportLoading.value = false
  batchImportStatusText.value = ''

  // 刷新列表
  if (added > 0) {
    await loadFavorites()
  }

  ElMessage.success(`导入完成：成功 ${added} 只，已存在 ${existed} 只，未识别 ${failed.length} 只`)
}

const handleUpdateFavorite = async () => {
  try {
    editLoading.value = true
    const payload = {
      notes: editForm.value.notes
    }
    const res = await favoritesApi.update(editForm.value.stock_code, payload as any)
    if ((res as any)?.success === false) throw new Error((res as any)?.message || '更新失败')
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    await loadFavorites()
  } catch (error: any) {
    console.error('更新自选股失败:', error)
    showError(error.message || '保存失败')
  } finally {
    editLoading.value = false
  }
}

const editFavorite = (row: any) => {
  editForm.value = {
    stock_code: row.stock_code,
    stock_name: row.stock_name,
    market: row.market || 'A股',
    industry: row.industry || '-',
    notes: row.notes || ''
  }
  editDialogVisible.value = true
}

const analyzeFavorite = (row: any) => {
  router.push({
    name: 'SingleAnalysis',
    query: { stock: row.stock_code, market: normalizeMarketForAnalysis(row.market || 'A股') }
  })
}

const removeFavorite = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要从自选股中移除 ${row.stock_name} 吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    const res = await favoritesApi.remove(row.stock_code)
    if ((res as any)?.success === false) throw new Error((res as any)?.message || '移除失败')
    ElMessage.success('移除成功')
    await loadFavorites()
  } catch (e) {
    // 用户取消或失败
  }
}

const viewStockDetail = (row: any) => {
  router.push({
    name: 'StockDetail',
    params: { code: String(row.stock_code || '').toUpperCase() }
  })
}

const getChangeClass = (changePercent: number) => {
  if (changePercent > 0) return 'text-red'
  if (changePercent < 0) return 'text-green'
  return ''
}

const formatPrice = (value: any): string => {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(2) : '-'
}

const formatPercent = (value: any): string => {
  const n = Number(value)
  if (!Number.isFinite(n)) return '-'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}

// 生命周期
onMounted(() => {
  loadFavorites().then(() => loadReportBadges())
})

onBeforeUnmount(() => {
  stopAutoRefresh()
})
</script>

<style lang="scss" scoped>
.favorites {
  .action-card {
    margin-bottom: 16px;

    .action-bar {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .search-input {
      width: 240px;
      margin-left: auto;
    }

    .action-buttons {
      display: flex;
      gap: 8px;
      flex-shrink: 0;
    }
  }

  /* 颜色选项样式 */
  .color-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 1px solid var(--glass-stroke-base);
    border-radius: 2px;
    margin-left: 8px;
    vertical-align: middle;
  }
  .color-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }
  .color-dot-preview {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 1px solid var(--glass-stroke-base);
    border-radius: 2px;
    margin-left: 6px;
    vertical-align: middle;
  }

  .favorites-list-card {
    .empty-state {
      padding: 40px;
      text-align: center;
    }

    .text-red {
      color: var(--stock-up);
    }

    .text-green {
      color: var(--stock-down);
    }
  }
}
</style>
