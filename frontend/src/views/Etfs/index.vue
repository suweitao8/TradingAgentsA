<template>
  <div class="etfs-page">
    <!-- 操作栏 -->
    <el-card class="action-card fade-in-up" shadow="never">
      <div class="action-bar">
        <div class="action-buttons">
          <el-button @click="refreshData" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
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
        :row-class-name="({ row }) => getEtfTypeClass(row.fund_type)"
      >
        <el-table-column type="index" label="#" width="55" align="center" />

        <el-table-column prop="fund_code" label="ETF代码" min-width="100">
          <template #default="{ row }">
            <router-link :to="`/stocks/${row.fund_code}`" class="fund-code-link">
              {{ row.fund_code }}
            </router-link>
          </template>
        </el-table-column>

        <el-table-column prop="fund_name" label="ETF名称" min-width="160">
          <template #default="{ row }">
            <span>{{ row.fund_name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="fund_type" label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTagType(row.fund_type)" size="small">{{ row.fund_type || '主题' }}</el-tag>
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

        <el-table-column label="1分MA" width="85" align="center">
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_1m">
              <span :class="slopeClass(row.ma_slope_1m.ma5)">MA5 {{ slopeArrow(row.ma_slope_1m.ma5) }}</span>
              <span :class="slopeClass(row.ma_slope_1m.ma10)">MA10 {{ slopeArrow(row.ma_slope_1m.ma10) }}</span>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="5分MA" width="85" align="center">
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_5m">
              <span :class="slopeClass(row.ma_slope_5m.ma5)">MA5 {{ slopeArrow(row.ma_slope_5m.ma5) }}</span>
              <span :class="slopeClass(row.ma_slope_5m.ma10)">MA10 {{ slopeArrow(row.ma_slope_5m.ma10) }}</span>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="15分MA" width="85" align="center">
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_15m">
              <span :class="slopeClass(row.ma_slope_15m.ma5)">MA5 {{ slopeArrow(row.ma_slope_15m.ma5) }}</span>
              <span :class="slopeClass(row.ma_slope_15m.ma10)">MA10 {{ slopeArrow(row.ma_slope_15m.ma10) }}</span>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="30分MA" width="85" align="center">
          <template #default="{ row }">
            <div class="ma-slope-cell" v-if="row.ma_slope_30m">
              <span :class="slopeClass(row.ma_slope_30m.ma5)">MA5 {{ slopeArrow(row.ma_slope_30m.ma5) }}</span>
              <span :class="slopeClass(row.ma_slope_30m.ma10)">MA10 {{ slopeArrow(row.ma_slope_30m.ma10) }}</span>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="备注" min-width="120">
          <template #default="{ row }">
            <span v-if="row.notes" class="notes-text">{{ row.notes }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="editEtf(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="removeEtf(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="!loading && etfs.length === 0" description="还没有 ETF，点击「批量导入」添加">
        <el-button type="primary" @click="showBatchImportDialog">批量导入</el-button>
      </el-empty>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑 ETF" width="480px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="代码">
          <el-input :model-value="editForm.fund_code" disabled />
        </el-form-item>
        <el-form-item label="名称">
          <el-input :model-value="editForm.fund_name" disabled />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="editForm.fund_type" placeholder="选择类型" style="width: 100%">
            <el-option label="宽基" value="宽基" />
            <el-option label="行业" value="行业" />
            <el-option label="主题" value="主题" />
            <el-option label="跨境" value="跨境" />
            <el-option label="策略" value="策略" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="3" placeholder="添加备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateEtf">保存</el-button>
      </template>
    </el-dialog>

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
import { Search, Refresh, Upload } from '@element-plus/icons-vue'
import { getEtfTypeClass } from '@/utils/industryColor'
import { etfsApi, type EtfItem, type AddEtfReq } from '@/api/etfs'
import { showError } from '@/utils/message'

// ---- 状态 ----
const etfs = ref<EtfItem[]>([])
const loading = ref(false)
const searchKeyword = ref('')

// 编辑对话框
const editDialogVisible = ref(false)
const editForm = ref<{ fund_code: string; fund_name: string; fund_type: string; notes: string }>({
  fund_code: '', fund_name: '', fund_type: '主题', notes: '',
})

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

// 均线斜率方向：1=上升↑ -1=下降↓ 0=走平→
function slopeArrow(val: number): string {
  if (val > 0) return '↑'
  if (val < 0) return '↓'
  return '→'
}

function slopeClass(val: number): string {
  if (val > 0) return 'text-danger'   // 上升=红（A 股惯例）
  if (val < 0) return 'text-success'  // 下降=绿
  return 'text-muted'                  // 走平=灰
}

function typeTagType(type: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    宽基: '',
    行业: 'success',
    主题: 'warning',
    跨境: 'info',
    策略: 'danger',
  }
  return map[type] || 'info'
}

// ---- 数据加载 ----
async function loadEtfs() {
  loading.value = true
  try {
    const res = await etfsApi.list()
    etfs.value = res.data || []
  } catch (e: any) {
    showError(e?.message || '加载 ETF 列表失败')
  } finally {
    loading.value = false
  }
}

async function refreshData() {
  await loadEtfs()
  ElMessage.success('已刷新')
}

// ---- 编辑 ----
function editEtf(row: EtfItem) {
  editForm.value = {
    fund_code: row.fund_code,
    fund_name: row.fund_name,
    fund_type: row.fund_type || '主题',
    notes: row.notes || '',
  }
  editDialogVisible.value = true
}

async function handleUpdateEtf() {
  try {
    await etfsApi.update(editForm.value.fund_code, {
      fund_type: editForm.value.fund_type,
      notes: editForm.value.notes,
    })
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    await loadEtfs()
  } catch (e: any) {
    showError(e?.message || '更新失败')
  }
}

// ---- 移除 ----
async function removeEtf(row: EtfItem) {
  try {
    await ElMessageBox.confirm(`确定移除 ${row.fund_name}（${row.fund_code}）？`, '移除 ETF', {
      confirmButtonText: '移除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await etfsApi.remove(row.fund_code)
    ElMessage.success('已移除')
    await loadEtfs()
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
    await loadEtfs()
  } catch (e: any) {
    showError(e?.message || '批量导入失败')
  } finally {
    batchLoading.value = false
  }
}

// ---- 生命周期 ----
// 每分钟自动刷新（静默，不显示 loading）
let etfRefreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  loadEtfs()
  etfRefreshTimer = setInterval(async () => {
    try {
      const res = await etfsApi.list()
      etfs.value = res.data || []
    } catch (e) {
      // 静默忽略
    }
  }, 60000)
})

onBeforeUnmount(() => {
  if (etfRefreshTimer) {
    clearInterval(etfRefreshTimer)
    etfRefreshTimer = null
  }
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
  font-size: 12px;
  font-family: 'Courier New', monospace;
  line-height: 1.4;
}
</style>
