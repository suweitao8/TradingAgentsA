<template>
  <el-drawer
    v-model="visible"
    :title="drawerTitle"
    direction="rtl"
    size="520px"
    :destroy-on-close="true"
    @open="handleOpen"
  >
    <div class="report-drawer">
      <!-- 顶部操作 -->
      <div class="drawer-actions">
        <el-radio-group v-model="activeTab" size="small">
          <el-radio-button label="daily">每日报告 ({{ reports.daily.length }})</el-radio-button>
          <el-radio-button label="realtime">盘中实时 ({{ reports.realtime.length }})</el-radio-button>
        </el-radio-group>
        <el-button
          size="small"
          type="primary"
          :loading="generating"
          @click="handleGenerate"
        >
          <el-icon><Refresh /></el-icon>
          立即生成{{ activeTab === 'daily' ? '每日' : '实时' }}
        </el-button>
      </div>

      <!-- 加载态 -->
      <div v-if="loading" class="loading-box">
        <el-skeleton :rows="8" animated />
      </div>

      <template v-else>
        <!-- 每日报告 Tab -->
        <div v-if="activeTab === 'daily'" class="tab-content">
          <div v-if="reports.daily.length === 0" class="empty-box">
            <el-empty description="暂无每日报告" :image-size="80" />
          </div>
          <div v-else class="report-list">
            <el-card
              v-for="r in reports.daily"
              :key="r.id"
              class="report-item"
              shadow="never"
            >
              <div class="report-item-header">
                <span class="report-date">{{ r.trade_date }}</span>
                <div class="report-tags">
                  <el-tag v-if="r.recommendation" :type="recommendTagType(r.recommendation)" size="small">
                    {{ r.recommendation }}
                  </el-tag>
                  <el-tag v-if="r.risk_level" type="warning" size="small">风险: {{ r.risk_level }}</el-tag>
                  <el-tag v-if="r.confidence_score" type="info" size="small">置信度 {{ Math.round(r.confidence_score) }}</el-tag>
                </div>
              </div>
              <div v-if="r.summary" class="report-summary">{{ r.summary }}</div>
              <div v-if="r.key_points && r.key_points.length" class="key-points">
                <ul>
                  <li v-for="(kp, i) in r.key_points" :key="i">{{ kp }}</li>
                </ul>
              </div>
              <div class="report-footer">
                <span v-if="r.model_info" class="meta">{{ r.model_info }}</span>
                <span class="meta">{{ formatTime(r.created_at) }}</span>
              </div>
            </el-card>
          </div>
        </div>

        <!-- 盘中实时 Tab -->
        <div v-else class="tab-content">
          <div v-if="reports.realtime.length === 0" class="empty-box">
            <el-empty description="暂无盘中实时报告（交易时段每小时自动生成）" :image-size="80" />
          </div>
          <div v-else class="report-list">
            <el-card
              v-for="r in reports.realtime"
              :key="r.id"
              class="report-item"
              shadow="never"
            >
              <div class="report-item-header">
                <span class="report-date">
                  {{ r.trade_date }} {{ r.hour_slot != null ? r.hour_slot + ':00' : '' }}
                </span>
                <div class="report-tags">
                  <el-tag v-if="r.recommendation" :type="recommendTagType(r.recommendation)" size="small">
                    {{ r.recommendation }}
                  </el-tag>
                  <el-tag v-if="r.risk_level" type="warning" size="small">风险: {{ r.risk_level }}</el-tag>
                </div>
              </div>
              <!-- 行情快照 -->
              <div v-if="r.quotes_snapshot" class="quotes-snapshot">
                <span class="quote-item">
                  价格 <strong>{{ fmtNum(r.quotes_snapshot.current_price) }}</strong>
                </span>
                <span class="quote-item" :class="chgClass(r.quotes_snapshot.change_percent)">
                  涨跌 <strong>{{ fmtPct(r.quotes_snapshot.change_percent) }}</strong>
                </span>
                <span class="quote-item">换手 <strong>{{ fmtNum(r.quotes_snapshot.turnover_rate, '%') }}</strong></span>
                <span class="quote-item">量比 <strong>{{ fmtNum(r.quotes_snapshot.volume_ratio) }}</strong></span>
              </div>
              <div v-if="r.commentary" class="report-summary">{{ r.commentary }}</div>
              <div v-if="r.key_points && r.key_points.length" class="key-points">
                <ul>
                  <li v-for="(kp, i) in r.key_points" :key="i">{{ kp }}</li>
                </ul>
              </div>
              <div class="report-footer">
                <span v-if="r.model_info" class="meta">{{ r.model_info }}</span>
                <span class="meta">{{ formatTime(r.created_at) }}</span>
              </div>
            </el-card>
          </div>
        </div>
      </template>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  favoriteReportsApi,
  type StockReportsResp,
} from '@/api/favorites'
import { showError } from '@/utils/message'

const props = defineProps<{
  modelValue: boolean
  stockCode: string
  stockName?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'generated'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const drawerTitle = computed(() => {
  const name = props.stockName || props.stockCode
  return `${name} 分析报告`
})

const activeTab = ref<'daily' | 'realtime'>('daily')
const loading = ref(false)
const generating = ref(false)
const reports = ref<StockReportsResp>({ daily: [], realtime: [] })

watch(() => props.stockCode, (code) => {
  if (code && visible.value) loadReports()
})

function handleOpen() {
  if (props.stockCode) loadReports()
}

async function loadReports() {
  if (!props.stockCode) return
  loading.value = true
  try {
    const resp = await favoriteReportsApi.getReports(props.stockCode, { limit: 20 })
    const data = (resp as any)?.data
    reports.value = data || { daily: [], realtime: [] }
    // 自动切到有数据的 tab
    if (reports.value.daily.length === 0 && reports.value.realtime.length > 0) {
      activeTab.value = 'realtime'
    } else {
      activeTab.value = 'daily'
    }
  } catch (e: any) {
    showError('加载报告失败：' + (e?.message || e))
    reports.value = { daily: [], realtime: [] }
  } finally {
    loading.value = false
  }
}

async function handleGenerate() {
  if (!props.stockCode) return
  generating.value = true
  try {
    const reportType = activeTab.value
    await favoriteReportsApi.generate({ report_type: reportType, stock_code: props.stockCode })
    ElMessage.success('生成任务已提交，请稍后刷新查看')
    emit('generated')
    // 延迟刷新（实时报告较快，每日报告较慢）
    const delay = reportType === 'realtime' ? 5000 : 30000
    setTimeout(() => loadReports(), delay)
  } catch (e: any) {
    showError('生成失败：' + (e?.message || e))
  } finally {
    generating.value = false
  }
}

function recommendTagType(rec?: string) {
  if (!rec) return 'info'
  if (/多|买入|看涨/.test(rec)) return 'success'
  if (/空|卖出|看跌/.test(rec)) return 'danger'
  return 'info'
}

function chgClass(v?: number | null) {
  if (v == null) return ''
  return v > 0 ? 'up' : v < 0 ? 'down' : ''
}

function fmtNum(v?: number | null, suffix = '') {
  if (v == null) return '-'
  return v.toFixed(2) + suffix
}

function fmtPct(v?: number | null) {
  if (v == null) return '-'
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}

function formatTime(t?: string) {
  if (!t) return ''
  try {
    const d = new Date(t)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return t
  }
}
</script>

<style scoped>
.report-drawer {
  padding: 0 4px;
}
.drawer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.loading-box,
.empty-box {
  padding: 40px 0;
}
.tab-content {
  min-height: 200px;
}
.report-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.report-item {
  border-radius: 8px;
}
.report-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.report-date {
  font-weight: 600;
  color: #303133;
}
.report-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.quotes-snapshot {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  padding: 8px 10px;
  background: var(--glass-bg-surface-hover);
  border-radius: 6px;
  margin-bottom: 8px;
  font-size: 13px;
}
.quote-item.up { color: var(--stock-up); }
.quote-item.down { color: var(--stock-down); }
.report-summary {
  font-size: 14px;
  line-height: 1.7;
  color: var(--glass-text-secondary);
  margin: 6px 0;
  white-space: pre-wrap;
}
.key-points ul {
  margin: 6px 0 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--glass-text-secondary);
  line-height: 1.7;
}
.report-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--glass-text-tertiary);
}
</style>
