<template>
  <div class="training-page">
    <section class="hero-card fade-in-up">
      <div class="hero-copy">
        <div class="hero-badge">AI 做 T 训练</div>
        <h1>基于真实历史行情的 A 股模拟做 T 训练</h1>
        <p>
          选择股票或 ETF，设定开始日期和本金，系统按时间顺序回放行情。
          训练过程中不会展示未来数据，结束后自动对比主动交易和买入持有的收益。
        </p>
      </div>

      <div class="hero-status">
        <div class="status-chip">
          <span class="status-label">会话</span>
          <span class="status-value">{{ session?.session_id || '未开始' }}</span>
        </div>
        <div class="status-chip">
          <span class="status-label">进度</span>
          <span class="status-value">{{ progressLabel }}</span>
        </div>
        <div class="status-chip">
          <span class="status-label">当前标的</span>
          <span class="status-value">{{ session?.symbol || selectedSymbol || '-' }}</span>
        </div>
      </div>
    </section>

    <el-row :gutter="20" class="training-grid">
      <el-col :xs="24" :lg="8">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>训练配置</span>
              <el-tag type="info" effect="light">MVP</el-tag>
            </div>
          </template>

          <el-form label-position="top" class="training-form">
            <el-form-item label="标的类型">
              <el-radio-group v-model="instrumentType" @change="onInstrumentTypeChange">
                <el-radio-button label="stock">股票</el-radio-button>
                <el-radio-button label="etf">ETF</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="选择标的">
              <el-select
                v-if="instrumentType === 'stock'"
                v-model="selectedSymbol"
                filterable
                remote
                reserve-keyword
                clearable
                placeholder="搜索股票代码或名称"
                :remote-method="remoteSearchStocks"
                :loading="stockSearchLoading"
                class="full-width"
              >
                <el-option
                  v-for="item in stockOptions"
                  :key="item.symbol"
                  :label="`${item.symbol} ${item.name}`"
                  :value="item.symbol"
                />
              </el-select>

              <el-select
                v-else
                v-model="selectedSymbol"
                filterable
                clearable
                placeholder="选择 ETF"
                class="full-width"
                @visible-change="onEtfSelectVisible"
              >
                <el-option
                  v-for="item in etfOptions"
                  :key="item.fund_code"
                  :label="`${item.fund_code} ${item.fund_name}`"
                  :value="item.fund_code"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="训练开始日期">
              <el-date-picker
                v-model="startDate"
                type="date"
                value-format="YYYY-MM-DD"
                format="YYYY-MM-DD"
                placeholder="选择历史开始日期"
                class="full-width"
              />
            </el-form-item>

            <el-form-item label="初始本金">
              <el-input-number
                v-model="initialCash"
                :min="10000"
                :step="10000"
                :precision="2"
                controls-position="right"
                class="full-width"
              />
            </el-form-item>

            <el-form-item label="训练天数">
              <el-input-number
                v-model="totalDays"
                :min="10"
                :max="120"
                :step="1"
                controls-position="right"
                class="full-width"
              />
            </el-form-item>

            <el-form-item label="训练备注">
              <el-input
                v-model="note"
                type="textarea"
                :rows="3"
                placeholder="可选，例如：趋势突破回放、均线做 T 练习"
              />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              class="full-width"
              :loading="creating"
              @click="createTraining"
            >
              开始训练
            </el-button>
          </el-form>
        </el-card>

        <el-card v-if="session" class="panel-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>交易控制</span>
              <el-tag :type="session.status === 'finished' ? 'success' : 'warning'" effect="light">
                {{ session.status === 'finished' ? '已结束' : '进行中' }}
              </el-tag>
            </div>
          </template>

          <div class="control-summary">
            <div class="summary-item">
              <span>当前日期</span>
              <strong>{{ step?.trade_date || session.start_date }}</strong>
            </div>
            <div class="summary-item">
              <span>当前价格</span>
              <strong>¥{{ formatMoney(currentPrice) }}</strong>
            </div>
            <div class="summary-item">
              <span>总资产</span>
              <strong>¥{{ formatMoney(session.total_equity) }}</strong>
            </div>
          </div>

          <el-divider />

          <el-radio-group v-model="tradeSide" class="full-width trade-side">
            <el-radio-button label="buy">买入</el-radio-button>
            <el-radio-button label="sell">卖出</el-radio-button>
          </el-radio-group>

          <el-input-number
            v-model="tradeQuantity"
            :min="100"
            :step="100"
            :precision="0"
            controls-position="right"
            class="full-width trade-quantity"
          />

          <div class="control-actions">
            <el-button
              type="primary"
              :loading="submitting"
              :disabled="!session"
              @click="submitTrade"
            >
              提交交易
            </el-button>
            <el-button :disabled="!session || step?.is_finished" @click="advanceStep">
              下一步
            </el-button>
            <el-button type="success" :loading="finishing" :disabled="!session" @click="finishTraining">
              结束训练
            </el-button>
          </div>
        </el-card>

        <el-card v-if="advice" class="panel-card coach-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>AI 教练</span>
              <el-tag type="success" effect="light">规则引擎</el-tag>
            </div>
          </template>

          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="趋势强弱">{{ advice.trend_strength }}</el-descriptions-item>
            <el-descriptions-item label="成交量">{{ advice.volume_change }}</el-descriptions-item>
            <el-descriptions-item label="做 T 适配">{{ advice.t_suitability }}</el-descriptions-item>
            <el-descriptions-item label="风险等级">{{ advice.risk_level }}</el-descriptions-item>
            <el-descriptions-item label="追高风险">{{ advice.chase_risk }}</el-descriptions-item>
            <el-descriptions-item label="低吸机会">{{ advice.dip_buy_suitability }}</el-descriptions-item>
            <el-descriptions-item label="建议仓位" :span="2">{{ advice.position_range }}</el-descriptions-item>
          </el-descriptions>

          <el-alert
            class="coach-reason"
            type="info"
            :closable="false"
            show-icon
            :title="advice.reason"
          />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="16">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>历史行情回放</span>
              <span class="panel-subtitle">当前窗口只展示已发生的数据</span>
            </div>
          </template>

          <el-table
            v-if="step?.visible_bars?.length"
            :data="step.visible_bars"
            style="width: 100%"
            height="360"
          >
            <el-table-column prop="trade_date" label="日期" width="120" />
            <el-table-column prop="open" label="开盘" width="95">
              <template #default="{ row }">{{ formatPrice(row.open) }}</template>
            </el-table-column>
            <el-table-column prop="high" label="最高" width="95">
              <template #default="{ row }">{{ formatPrice(row.high) }}</template>
            </el-table-column>
            <el-table-column prop="low" label="最低" width="95">
              <template #default="{ row }">{{ formatPrice(row.low) }}</template>
            </el-table-column>
            <el-table-column prop="close" label="收盘" width="95">
              <template #default="{ row }">{{ formatPrice(row.close) }}</template>
            </el-table-column>
            <el-table-column prop="volume" label="成交量">
              <template #default="{ row }">{{ formatVolume(row.volume) }}</template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="先创建训练会话，才能看到回放窗口" />
        </el-card>

        <el-card v-if="session" class="panel-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>持仓与盈亏</span>
              <span class="panel-subtitle">系统按 A 股基础交易规则计算</span>
            </div>
          </template>

          <el-row :gutter="16" class="metric-grid">
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>现金</span>
                <strong>¥{{ formatMoney(session.cash) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>持仓数量</span>
                <strong>{{ positionQuantity }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>持仓市值</span>
                <strong>¥{{ formatMoney(positionMarketValue) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>总资产</span>
                <strong>¥{{ formatMoney(session.total_equity) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>已实现盈亏</span>
                <strong :class="pnlClass(session.realized_pnl)">¥{{ formatMoney(session.realized_pnl) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>未实现盈亏</span>
                <strong :class="pnlClass(session.unrealized_pnl)">¥{{ formatMoney(session.unrealized_pnl) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>交易次数</span>
                <strong>{{ session.trade_count }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>当前进度</span>
                <strong>{{ progressLabel }}</strong>
              </div>
            </el-col>
          </el-row>

          <el-card v-if="session.positions.length" class="position-card" shadow="never">
            <template #header>当前持仓</template>
            <el-table :data="session.positions" size="small" style="width: 100%">
              <el-table-column prop="symbol" label="标的" width="120" />
              <el-table-column prop="quantity" label="数量" width="100" />
              <el-table-column prop="avg_cost" label="均价" width="100">
                <template #default="{ row }">{{ formatPrice(row.avg_cost) }}</template>
              </el-table-column>
              <el-table-column prop="market_value" label="市值" width="110">
                <template #default="{ row }">{{ formatMoney(row.market_value) }}</template>
              </el-table-column>
              <el-table-column prop="unrealized_pnl" label="浮盈浮亏">
                <template #default="{ row }">
                  <span :class="pnlClass(row.unrealized_pnl)">{{ formatMoney(row.unrealized_pnl) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-card>

        <el-card v-if="report" class="panel-card report-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>赛后复盘报告</span>
              <el-tag type="success" effect="light">已生成</el-tag>
            </div>
          </template>

          <el-row :gutter="16" class="metric-grid">
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>主动收益</span>
                <strong :class="returnClass(report.active_return)">{{ formatPercent(report.active_return) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>持有收益</span>
                <strong :class="returnClass(report.buy_and_hold_return)">{{ formatPercent(report.buy_and_hold_return) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>超额收益</span>
                <strong :class="returnClass(report.excess_return)">{{ formatPercent(report.excess_return) }}</strong>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>最大回撤</span>
                <strong>{{ formatPercent(report.max_drawdown) }}</strong>
              </div>
            </el-col>
          </el-row>

          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="结束日期">{{ report.end_date }}</el-descriptions-item>
            <el-descriptions-item label="交易次数">{{ report.trade_count }}</el-descriptions-item>
            <el-descriptions-item label="最终现金">¥{{ formatMoney(report.final_cash) }}</el-descriptions-item>
            <el-descriptions-item label="最终总资产">¥{{ formatMoney(report.final_equity) }}</el-descriptions-item>
            <el-descriptions-item label="已实现盈亏">¥{{ formatMoney(report.realized_pnl) }}</el-descriptions-item>
            <el-descriptions-item label="未实现盈亏">¥{{ formatMoney(report.unrealized_pnl) }}</el-descriptions-item>
          </el-descriptions>

          <el-alert class="report-advice" type="success" :closable="false" show-icon :title="report.advice" />

          <el-row :gutter="16" class="report-lists">
            <el-col :xs="24" :md="12">
              <el-card shadow="never" class="inner-card">
                <template #header>成功交易</template>
                <el-empty v-if="report.good_trades.length === 0" description="暂无" :image-size="60" />
                <el-scrollbar v-else max-height="220px">
                  <div v-for="(trade, index) in report.good_trades" :key="index" class="trade-item good">
                    <div class="trade-title">
                      <strong>{{ trade.side === 'buy' ? '买入' : '卖出' }}</strong>
                      <span>{{ trade.trade_date || trade.executed_price || '' }}</span>
                    </div>
                    <div class="trade-meta">
                      <span>价格 {{ formatPrice(trade.executed_price ?? trade.price) }}</span>
                      <span>数量 {{ trade.quantity }}</span>
                    </div>
                  </div>
                </el-scrollbar>
              </el-card>
            </el-col>

            <el-col :xs="24" :md="12">
              <el-card shadow="never" class="inner-card">
                <template #header>可能有问题的交易</template>
                <el-empty v-if="report.bad_trades.length === 0" description="暂无" :image-size="60" />
                <el-scrollbar v-else max-height="220px">
                  <div v-for="(trade, index) in report.bad_trades" :key="index" class="trade-item bad">
                    <div class="trade-title">
                      <strong>{{ trade.side === 'buy' ? '买入' : '卖出' }}</strong>
                      <span>{{ trade.trade_date || trade.executed_price || '' }}</span>
                    </div>
                    <div class="trade-meta">
                      <span>价格 {{ formatPrice(trade.executed_price ?? trade.price) }}</span>
                      <span>数量 {{ trade.quantity }}</span>
                    </div>
                  </div>
                </el-scrollbar>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { analysisApi } from '@/api/analysis'
import { etfsApi } from '@/api/etfs'
import { trainingApi, type TrainingAdvice, type TrainingReport, type TrainingReplayStep, type TrainingSessionResponse } from '@/api/training'

interface StockOption {
  symbol: string
  name: string
  market?: string
}

interface EtfOption {
  fund_code: string
  fund_name: string
  fund_type: string
}

const route = useRoute()
const router = useRouter()

const instrumentType = ref<'stock' | 'etf'>('stock')
const selectedSymbol = ref('')
const startDate = ref('')
const initialCash = ref(100000)
const totalDays = ref(30)
const note = ref('')
const creating = ref(false)
const submitting = ref(false)
const finishing = ref(false)
const stockSearchLoading = ref(false)

const stockOptions = ref<StockOption[]>([])
const etfOptions = ref<EtfOption[]>([])

const session = ref<TrainingSessionResponse | null>(null)
const step = ref<TrainingReplayStep | null>(null)
const report = ref<TrainingReport | null>(null)
const advice = ref<TrainingAdvice | null>(null)

const tradeSide = ref<'buy' | 'sell'>('buy')
const tradeQuantity = ref(100)

let stockSearchTimer: number | null = null

const currentPrice = computed(() => {
  const bars = step.value?.visible_bars || []
  const fromStep = step.value?.current_price ?? bars[bars.length - 1]?.close
  if (typeof fromStep === 'number' && Number.isFinite(fromStep)) {
    return fromStep
  }
  const fromSession = session.value?.positions?.[0]?.avg_cost
  return typeof fromSession === 'number' ? fromSession : 0
})

const positionQuantity = computed(() => session.value?.positions?.[0]?.quantity ?? 0)
const positionMarketValue = computed(() => session.value?.positions?.[0]?.market_value ?? 0)
const progressLabel = computed(() => {
  if (!session.value) {
    return '0 / 0'
  }
  const current = Math.min(session.value.current_step + 1, session.value.total_days)
  return `${current} / ${session.value.total_days}`
})

function formatPrice(value: unknown) {
  const num = Number(value ?? 0)
  return Number.isFinite(num) ? num.toFixed(2) : '-'
}

function formatMoney(value: unknown) {
  const num = Number(value ?? 0)
  return Number.isFinite(num) ? num.toFixed(2) : '-'
}

function formatVolume(value: unknown) {
  const num = Number(value ?? 0)
  if (!Number.isFinite(num)) {
    return '-'
  }
  if (num >= 100000000) return `${(num / 100000000).toFixed(2)} 亿`
  if (num >= 10000) return `${(num / 10000).toFixed(2)} 万`
  return num.toFixed(0)
}

function formatPercent(value: unknown) {
  const num = Number(value ?? 0)
  return Number.isFinite(num) ? `${(num * 100).toFixed(2)}%` : '-'
}

function pnlClass(value: unknown) {
  const num = Number(value ?? 0)
  if (num > 0) return 'positive'
  if (num < 0) return 'negative'
  return ''
}

function returnClass(value: unknown) {
  return pnlClass(value)
}

async function loadEtfOptions() {
  if (etfOptions.value.length > 0) {
    return
  }
  try {
    const res = await etfsApi.popular()
    etfOptions.value = res.data || []
  } catch (error: any) {
    ElMessage.error(error?.message || '加载 ETF 列表失败')
  }
}

async function remoteSearchStocks(query: string) {
  if (stockSearchTimer) {
    window.clearTimeout(stockSearchTimer)
  }
  if (!query || query.trim().length < 2) {
    stockOptions.value = []
    return
  }

  stockSearchTimer = window.setTimeout(async () => {
    stockSearchLoading.value = true
    try {
      const res = await analysisApi.searchStocks(query.trim(), 'A股')
      const list = Array.isArray((res as any)?.data)
        ? (res as any).data
        : Array.isArray(res)
          ? res
          : []
      stockOptions.value = list.slice(0, 20)
    } catch (error: any) {
      ElMessage.error(error?.message || '搜索股票失败')
    } finally {
      stockSearchLoading.value = false
    }
  }, 200)
}

async function onEtfSelectVisible(visible: boolean) {
  if (visible) {
    await loadEtfOptions()
  }
}

function onInstrumentTypeChange() {
  selectedSymbol.value = ''
  stockOptions.value = []
  if (instrumentType.value === 'etf') {
    void loadEtfOptions()
  }
}

async function loadStep(sessionId: string) {
  const res = await trainingApi.getStep(sessionId)
  step.value = res.data
  advice.value = res.data?.advice || null
  if (res.data?.session) {
    session.value = res.data.session
  }
}

async function loadSession(sessionId: string) {
  const res = await trainingApi.getSession(sessionId)
  session.value = res.data
  if (res.data.status === 'finished') {
    const reportRes = await trainingApi.getReport(sessionId)
    report.value = reportRes.data
  }
  await loadStep(sessionId)
}

async function createTraining() {
  if (!selectedSymbol.value) {
    ElMessage.warning('请先选择标的')
    return
  }
  if (!startDate.value) {
    ElMessage.warning('请先选择训练开始日期')
    return
  }

  creating.value = true
  try {
    const res = await trainingApi.createSession({
      symbol: selectedSymbol.value,
      start_date: startDate.value,
      initial_cash: initialCash.value,
      total_days: totalDays.value,
      market: 'CN',
      note: note.value || undefined,
    })
    session.value = res.data
    report.value = null
    await router.replace({ path: '/training', query: { sessionId: res.data.session_id } })
    await loadStep(res.data.session_id)
    tradeQuantity.value = 100
    ElMessage.success('训练已开始')
  } catch (error: any) {
    ElMessage.error(error?.message || '创建训练会话失败')
  } finally {
    creating.value = false
  }
}

async function submitTrade() {
  if (!session.value) {
    ElMessage.warning('请先开始训练')
    return
  }
  if (!currentPrice.value) {
    ElMessage.warning('当前没有可用价格')
    return
  }

  submitting.value = true
  try {
    const res = await trainingApi.submitAction(session.value.session_id, {
      side: tradeSide.value,
      quantity: tradeQuantity.value,
      price: currentPrice.value,
      trade_date: step.value?.trade_date,
    })
    session.value = res.data
    await loadStep(session.value.session_id)
    ElMessage.success('交易已提交')
  } catch (error: any) {
    ElMessage.error(error?.message || '提交交易失败')
  } finally {
    submitting.value = false
  }
}

async function advanceStep() {
  if (!session.value) {
    return
  }
  try {
    const res = await trainingApi.advance(session.value.session_id)
    step.value = res.data
    advice.value = res.data?.advice || null
    if (res.data?.session) {
      session.value = res.data.session
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '推进训练失败')
  }
}

async function finishTraining() {
  if (!session.value) {
    return
  }
  finishing.value = true
  try {
    const res = await trainingApi.finish(session.value.session_id)
    report.value = res.data
    session.value = { ...session.value, status: 'finished' }
    ElMessage.success('训练已结束，报告已生成')
  } catch (error: any) {
    ElMessage.error(error?.message || '生成复盘报告失败')
  } finally {
    finishing.value = false
  }
}

watch(
  () => route.query.sessionId,
  async (sessionId) => {
    if (typeof sessionId === 'string' && sessionId) {
      try {
        await loadSession(sessionId)
      } catch (error: any) {
        ElMessage.error(error?.message || '恢复训练会话失败')
      }
    }
  },
  { immediate: true }
)

onMounted(() => {
  void loadEtfOptions()
})
</script>

<style scoped lang="scss">
.training-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(17, 24, 39, 0.94), rgba(15, 118, 110, 0.78));
  color: #f8fafc;
  box-shadow: var(--glass-shadow-lg);
}

.hero-copy {
  max-width: 760px;

  h1 {
    margin: 10px 0 12px;
    font-size: 32px;
    line-height: 1.15;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.82);
    line-height: 1.7;
    max-width: 720px;
  }
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-status {
  display: grid;
  gap: 12px;
  min-width: 240px;
}

.status-chip {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.status-label {
  display: block;
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 6px;
}

.status-value {
  font-size: 14px;
  font-weight: 600;
}

.training-grid {
  align-items: flex-start;
}

.panel-card {
  margin-bottom: 20px;
  border-radius: 18px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
}

.panel-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: 400;
}

.training-form {
  :deep(.el-form-item__label) {
    font-weight: 600;
  }
}

.full-width {
  width: 100%;
}

.control-summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.summary-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);

  span {
    display: block;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-bottom: 6px;
  }

  strong {
    font-size: 15px;
  }
}

.trade-side {
  margin-bottom: 14px;
}

.trade-quantity {
  margin-bottom: 14px;
}

.control-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.coach-card :deep(.el-descriptions__label) {
  width: 96px;
}

.coach-reason,
.report-advice {
  margin-top: 14px;
}

.metric-grid {
  margin-bottom: 12px;
}

.metric-box {
  padding: 14px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.92), rgba(241, 245, 249, 0.92));
  border: 1px solid var(--el-border-color-lighter);

  span {
    display: block;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-bottom: 8px;
  }

  strong {
    font-size: 16px;
  }
}

.positive {
  color: var(--el-color-danger);
}

.negative {
  color: var(--el-color-success);
}

.position-card,
.inner-card {
  margin-top: 16px;
}

.report-card :deep(.el-descriptions) {
  margin-top: 12px;
}

.report-lists {
  margin-top: 16px;
}

.trade-item {
  padding: 12px 14px;
  border-radius: 14px;
  margin-bottom: 10px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.trade-item.good {
  border-color: rgba(16, 185, 129, 0.24);
}

.trade-item.bad {
  border-color: rgba(239, 68, 68, 0.22);
}

.trade-title,
.trade-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.trade-title {
  margin-bottom: 6px;
}

.trade-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 1024px) {
  .hero-card {
    flex-direction: column;
  }

  .hero-status {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .control-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .control-actions {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card {
    padding: 20px;
  }

  .hero-copy h1 {
    font-size: 26px;
  }

  .hero-status {
    grid-template-columns: 1fr;
  }

  .control-summary {
    grid-template-columns: 1fr;
  }
}
</style>
