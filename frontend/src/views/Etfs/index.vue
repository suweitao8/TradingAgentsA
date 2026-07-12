<template>
  <div class="etfs-page">
    <!-- 操作栏 -->
    <el-card class="action-card fade-in-up" shadow="never">
      <div class="action-bar">
        <div class="action-buttons">
          <el-button type="success" @click="showBatchImportDialog">
            <el-icon><Upload /></el-icon>
            批量导入
          </el-button>
        </div>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索 ETF 代码或名称"
          clearable
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </el-card>

    <!-- ETF 列表 -->
    <el-card class="etfs-list-card" shadow="never">
      <el-table
        :data="filteredEtfs"
        v-loading="loading"
        style="width: 100%"
        border
        :row-class-name="({ row }) => getEtfTypeClass(row.fund_type)"
      >
        <el-table-column type="index" label="#" width="45" align="center" />

        <el-table-column prop="fund_code" label="代码" width="75" align="center">
          <template #default="{ row }">
            <router-link :to="`/stocks/${row.fund_code}`" class="fund-code-link">
              {{ row.fund_code }}
            </router-link>
          </template>
        </el-table-column>

        <el-table-column prop="fund_name" label="名称" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.fund_name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="最新价" width="90" align="right">
          <template #default="{ row }">
            <span v-if="row.current_price != null" class="price-value">{{ row.current_price.toFixed(3) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="涨跌幅" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.change_percent != null" :class="pctClass(row.change_percent)">
              {{ row.change_percent > 0 ? '+' : '' }}{{ row.change_percent.toFixed(2) }}%
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="换手率" width="90" align="right">
          <template #default="{ row }">
            <span v-if="row.turnover_rate != null">{{ row.turnover_rate.toFixed(2) }}%</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="量比" width="80" align="right">
          <template #default="{ row }">
            <span v-if="row.volume_ratio != null" :class="{ 'text-danger': row.volume_ratio >= 2, 'text-warning': row.volume_ratio >= 1 && row.volume_ratio < 2 }">
              {{ row.volume_ratio.toFixed(2) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="1分MA" width="130" align="center">
          <template #header>
            <div class="ma-header">1分MA</div>
            <div class="ma-sub-header">
              <span>2分前</span><span>1分前</span><span>当前</span>
            </div>
          </template>
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_1m">
              <div class="ma-row" title="MA5 均线度数">
                <span :class="slopeClass(row.ma_slope_1m.ma5?.prev2)">{{ slopeArrow(row.ma_slope_1m.ma5?.prev2) }}{{ slopeVal(row.ma_slope_1m.ma5?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_1m.ma5?.prev)">{{ slopeArrow(row.ma_slope_1m.ma5?.prev) }}{{ slopeVal(row.ma_slope_1m.ma5?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_1m.ma5?.now)">{{ slopeArrow(row.ma_slope_1m.ma5?.now) }}{{ slopeVal(row.ma_slope_1m.ma5?.now) }}</span>
              </div>
              <div class="ma-row" title="MA10 均线度数">
                <span :class="slopeClass(row.ma_slope_1m.ma10?.prev2)">{{ slopeArrow(row.ma_slope_1m.ma10?.prev2) }}{{ slopeVal(row.ma_slope_1m.ma10?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_1m.ma10?.prev)">{{ slopeArrow(row.ma_slope_1m.ma10?.prev) }}{{ slopeVal(row.ma_slope_1m.ma10?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_1m.ma10?.now)">{{ slopeArrow(row.ma_slope_1m.ma10?.now) }}{{ slopeVal(row.ma_slope_1m.ma10?.now) }}</span>
              </div>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="5分MA" width="130" align="center">
          <template #header>
            <div class="ma-header">5分MA</div>
            <div class="ma-sub-header">
              <span>2分前</span><span>1分前</span><span>当前</span>
            </div>
          </template>
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_5m">
              <div class="ma-row" title="MA5 均线度数">
                <span :class="slopeClass(row.ma_slope_5m.ma5?.prev2)">{{ slopeArrow(row.ma_slope_5m.ma5?.prev2) }}{{ slopeVal(row.ma_slope_5m.ma5?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_5m.ma5?.prev)">{{ slopeArrow(row.ma_slope_5m.ma5?.prev) }}{{ slopeVal(row.ma_slope_5m.ma5?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_5m.ma5?.now)">{{ slopeArrow(row.ma_slope_5m.ma5?.now) }}{{ slopeVal(row.ma_slope_5m.ma5?.now) }}</span>
              </div>
              <div class="ma-row" title="MA10 均线度数">
                <span :class="slopeClass(row.ma_slope_5m.ma10?.prev2)">{{ slopeArrow(row.ma_slope_5m.ma10?.prev2) }}{{ slopeVal(row.ma_slope_5m.ma10?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_5m.ma10?.prev)">{{ slopeArrow(row.ma_slope_5m.ma10?.prev) }}{{ slopeVal(row.ma_slope_5m.ma10?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_5m.ma10?.now)">{{ slopeArrow(row.ma_slope_5m.ma10?.now) }}{{ slopeVal(row.ma_slope_5m.ma10?.now) }}</span>
              </div>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="15分MA" width="130" align="center">
          <template #header>
            <div class="ma-header">15分MA</div>
            <div class="ma-sub-header">
              <span>2分前</span><span>1分前</span><span>当前</span>
            </div>
          </template>
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_15m">
              <div class="ma-row" title="MA5 均线度数">
                <span :class="slopeClass(row.ma_slope_15m.ma5?.prev2)">{{ slopeArrow(row.ma_slope_15m.ma5?.prev2) }}{{ slopeVal(row.ma_slope_15m.ma5?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_15m.ma5?.prev)">{{ slopeArrow(row.ma_slope_15m.ma5?.prev) }}{{ slopeVal(row.ma_slope_15m.ma5?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_15m.ma5?.now)">{{ slopeArrow(row.ma_slope_15m.ma5?.now) }}{{ slopeVal(row.ma_slope_15m.ma5?.now) }}</span>
              </div>
              <div class="ma-row" title="MA10 均线度数">
                <span :class="slopeClass(row.ma_slope_15m.ma10?.prev2)">{{ slopeArrow(row.ma_slope_15m.ma10?.prev2) }}{{ slopeVal(row.ma_slope_15m.ma10?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_15m.ma10?.prev)">{{ slopeArrow(row.ma_slope_15m.ma10?.prev) }}{{ slopeVal(row.ma_slope_15m.ma10?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_15m.ma10?.now)">{{ slopeArrow(row.ma_slope_15m.ma10?.now) }}{{ slopeVal(row.ma_slope_15m.ma10?.now) }}</span>
              </div>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="30分MA" width="130" align="center">
          <template #header>
            <div class="ma-header">30分MA</div>
            <div class="ma-sub-header">
              <span>2分前</span><span>1分前</span><span>当前</span>
            </div>
          </template>
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_30m">
              <div class="ma-row" title="MA5 均线度数">
                <span :class="slopeClass(row.ma_slope_30m.ma5?.prev2)">{{ slopeArrow(row.ma_slope_30m.ma5?.prev2) }}{{ slopeVal(row.ma_slope_30m.ma5?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_30m.ma5?.prev)">{{ slopeArrow(row.ma_slope_30m.ma5?.prev) }}{{ slopeVal(row.ma_slope_30m.ma5?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_30m.ma5?.now)">{{ slopeArrow(row.ma_slope_30m.ma5?.now) }}{{ slopeVal(row.ma_slope_30m.ma5?.now) }}</span>
              </div>
              <div class="ma-row" title="MA10 均线度数">
                <span :class="slopeClass(row.ma_slope_30m.ma10?.prev2)">{{ slopeArrow(row.ma_slope_30m.ma10?.prev2) }}{{ slopeVal(row.ma_slope_30m.ma10?.prev2) }}</span>
                <span :class="slopeClass(row.ma_slope_30m.ma10?.prev)">{{ slopeArrow(row.ma_slope_30m.ma10?.prev) }}{{ slopeVal(row.ma_slope_30m.ma10?.prev) }}</span>
                <span :class="slopeClass(row.ma_slope_30m.ma10?.now)">{{ slopeArrow(row.ma_slope_30m.ma10?.now) }}{{ slopeVal(row.ma_slope_30m.ma10?.now) }}</span>
              </div>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="" width="55" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="danger" @click="removeEtf(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="!loading && etfs.length === 0" description="还没有 ETF，点击「批量导入」添加">
        <el-button type="primary" @click="showBatchImportDialog">批量导入</el-button>
      </el-empty>
    </el-card>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="batchDialogVisible" title="批量导入 ETF" width="560px">
      <el-alert type="info" :closable="false" style="margin-bottom: 12px">
        每行一个，支持以下格式：① 每行一个代码（如 510300）② 代码,名称 ③ 代码,名称,类型
      </el-alert>
      <el-input
        v-model="batchInputText"
        type="textarea"
        :rows="8"
        placeholder="510300,沪深300ETF,宽基&#10;512480,半导体ETF,主题&#10;512010,医药ETF,行业"
      />
      <div v-if="batchResult" style="margin-top: 12px">
        <el-alert
          :type="batchResult.failed.length > 0 ? 'warning' : 'success'"
          :title="`成功 ${batchResult.added.length} / 已存在 ${batchResult.existed.length} / 失败 ${batchResult.failed.length}`"
          :closable="false"
        />
      </div>
      <template #footer>
        <el-button @click="batchDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleBatchImport" :loading="batchLoading">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Upload, Delete } from '@element-plus/icons-vue'
import { getEtfTypeClass } from '@/utils/industryColor'
import { etfsApi, type EtfItem, type AddEtfReq } from '@/api/etfs'
import { showError } from '@/utils/message'

// ---- 状态 ----
const etfs = ref<EtfItem[]>([])
const loading = ref(false)
const searchKeyword = ref('')

// 批量导入
const batchDialogVisible = ref(false)
const batchInputText = ref('')
const batchLoading = ref(false)
const batchResult = ref<{ added: string[]; existed: string[]; failed: string[] } | null>(null)

// ---- 计算属性 ----
const filteredEtfs = computed(() => {
  if (!searchKeyword.value) return etfs.value
  const kw = searchKeyword.value.toLowerCase()
  return etfs.value.filter(
    (e) => e.fund_code.includes(kw) || e.fund_name.toLowerCase().includes(kw),
  )
})

// ---- 工具函数 ----
function pctClass(pct: number): string {
  if (pct > 0) return 'text-danger'
  if (pct < 0) return 'text-success'
  return ''
}

// 均线斜率（度数）：>0上升↑ <0下降↓ ≈0走平→
function slopeArrow(val?: number): string {
  if (val === undefined || val === null) return '-'
  if (val > 0.1) return '↑'
  if (val < -0.1) return '↓'
  return '→'
}

function slopeClass(val?: number): string {
  if (val === undefined || val === null) return 'text-muted'
  if (val > 0.1) return 'text-danger'   // 上升=红（A 股惯例）
  if (val < -0.1) return 'text-success'  // 下降=绿
  return 'text-muted'                    // 走平=灰
}

// 格式化度数显示：四舍五入取整，去负号（颜色已区分），如 -2.9 → "3°"
function slopeVal(val?: number): string {
  if (val === undefined || val === null) return ''
  return `${Math.round(Math.abs(val))}°`
}

// ---- 数据加载 ----
// 首次加载显示 loading；有旧数据时静默刷新（不转圈），拉取成功后才更新
async function loadEtfs() {
  const isFirstLoad = etfs.value.length === 0
  if (isFirstLoad) loading.value = true
  try {
    const res = await etfsApi.list()
    etfs.value = res.data || []
  } catch (e: any) {
    if (isFirstLoad) showError(e?.message || '加载 ETF 列表失败')
  } finally {
    if (isFirstLoad) loading.value = false
  }
}

// ---- 移除 ----
async function removeEtf(row: EtfItem | null) {
  if (!row) return
  try {
    await ElMessageBox.confirm(`确定移除 ${row.fund_name}（${row.fund_code}）？`, '移除 ETF', {
      confirmButtonText: '移除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await etfsApi.remove(row.fund_code)
    ElMessage.success('已移除')
    loadEtfs()
  } catch (e: any) {
    if (e !== 'cancel' && e?.message) {
      showError(e.message)
    }
  }
}

// ---- 批量导入 ----
function showBatchImportDialog() {
  batchInputText.value = ''
  batchResult.value = null
  batchDialogVisible.value = true
}

async function handleBatchImport() {
  const text = batchInputText.value.trim()
  if (!text) {
    ElMessage.warning('请输入 ETF 信息')
    return
  }

  batchLoading.value = true
  try {
    // 支持两种格式：
    // ① 每行一个代码（6位数字），名称和类型自动补
    // ② 代码,名称 或 代码,名称,类型
    const lines = text.split('\n').filter((l) => l.trim())
    const items: AddEtfReq[] = []
    for (const line of lines) {
      const parts = line.trim().split(/[,，\s]+/).filter((p) => p)
      if (!parts.length) continue
      const code = parts[0].trim()
      // 跳过明显不是代码的行（非数字开头且不足5位）
      if (!/^\d{5,6}$/.test(code)) continue
      items.push({
        fund_code: code,
        fund_name: parts[1]?.trim() || `ETF${code}`,
        fund_type: parts[2]?.trim() || '主题',
      })
    }

    if (!items.length) {
      ElMessage.warning('未解析到有效条目，请输入6位ETF代码（每行一个或用逗号分隔代码和名称）')
      return
    }

    const result = await etfsApi.batchAdd(items)
    batchResult.value = result.data
    ElMessage.success(result.message || '导入完成')
    batchDialogVisible.value = false
    // 静默刷新列表（不显示 loading 转圈，后台慢慢加载行情数据）
    loadEtfs()
  } catch (e: any) {
    showError(e?.message || '批量导入失败')
  } finally {
    batchLoading.value = false
  }
}

// ---- 自动刷新：盘中递归轮询（刷新成功后立刻下一次），盘后不刷新 ----

// 判断是否在 A 股交易时段（9:25-11:30, 13:00-15:00，周一至周五）
function isTradingTime(): boolean {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false  // 周末

  const h = now.getHours()
  const m = now.getMinutes()
  const minutes = h * 60 + m

  // 集合竞价 9:20 + 连续竞价 9:30-11:30 + 13:00-15:00
  if (minutes >= 560 && minutes <= 690) return true   // 9:20-11:30
  if (minutes >= 780 && minutes <= 900) return true   // 13:00-15:00
  return false
}

let autoRefreshActive = false

async function autoRefreshLoop() {
  if (!autoRefreshActive) return

  // 非交易时段：每 30 秒检查一次是否进入交易时段
  if (!isTradingTime()) {
    setTimeout(autoRefreshLoop, 30000)
    return
  }

  // 交易时段：拉取数据，成功后立刻下一轮
  try {
    const res = await etfsApi.list()
    etfs.value = res.data || []
  } catch {
    // 静默忽略
  }
  // 递归（成功或失败都继续下一轮，保持盘中持续刷新）
  if (autoRefreshActive) {
    setTimeout(autoRefreshLoop, 2000)  // 2 秒间隔，接近实时
  }
}

onMounted(async () => {
  await loadEtfs()
  // 启动自动刷新循环
  autoRefreshActive = true
  autoRefreshLoop()
})

onBeforeUnmount(() => {
  autoRefreshActive = false
})
</script>

<style scoped>
.etfs-page {
  padding: 16px;
}

.action-card {
  margin-bottom: 12px;
}

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

.etfs-list-card {
  min-height: 400px;
}

.fund-code-link {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: var(--accent-cyan);
  text-decoration: none;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 0.8;
    text-decoration: underline;
  }
}

.price-value {
  font-weight: 600;
}

.text-danger {
  color: var(--el-color-danger);
  font-weight: 600;
}

.text-success {
  color: var(--el-color-success);
  font-weight: 600;
}

.text-warning {
  color: var(--el-color-warning);
  font-weight: 600;
}

.text-muted {
  color: var(--el-text-color-placeholder);
}

.notes-text {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.ma-slope-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.4;
  font-size: 11px;
  font-family: 'Courier New', monospace;
}

/* 每行 3 等分（2分前/1分前/当前），MA5 一行、MA10 一行 */
.ma-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  align-items: center;
  column-gap: 2px;
}

/* MA 列分组表头 */
.ma-header {
  font-weight: 600;
  font-size: 12px;
  line-height: 1.2;
}

.ma-sub-header {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  column-gap: 2px;
  font-size: 10px;
  color: var(--el-text-color-placeholder);
  font-weight: 400;
  margin-top: 1px;
}

.ma-arrow {
  font-size: 16px;
  font-weight: 700;
  cursor: default;
}
</style>
