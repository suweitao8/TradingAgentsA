<template>
  <div class="training-page">
    <section class="overview-card fade-in-up">
      <div class="overview-header">
        <div class="overview-copy">
          <div class="overview-badge">模拟炒股</div>
          <h1>训练总览</h1>
          <p>基于真实历史行情的 30 日回放训练，只展示当前时间点之前的数据，并对比主动做 T、买入持有与综合评分。</p>
        </div>

        <div class="overview-actions">
          <el-button type="primary" :loading="creating" @click="createTraining">
            新建存档
          </el-button>
          <div class="overview-chip">
            <span>会话</span>
            <strong>{{ session?.session_id || '未开始' }}</strong>
          </div>
          <div class="overview-chip">
            <span>标的</span>
            <strong>{{ session?.symbol_name || session?.symbol || selectedSymbol || '-' }}</strong>
          </div>
          <div class="overview-chip">
            <span>评分</span>
            <strong>{{ formatScore(report?.score) }}</strong>
          </div>
        </div>
      </div>

      <el-table :data="overviewRows" class="overview-table" size="small" :show-header="false">
        <el-table-column prop="label" width="160" />
        <el-table-column prop="value" min-width="220" />
        <el-table-column prop="note" min-width="240">
          <template #default="{ row }">
            <div class="overview-note">
              <span>{{ row.note }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
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
                clearable
                placeholder="从自选股票中选择"
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
                placeholder="从自选 ETF 中选择"
                class="full-width"
              >
                <el-option
                  v-for="item in etfOptions"
                  :key="item.fund_code"
                  :label="`${item.fund_code} ${item.fund_name}`"
                  :value="item.fund_code"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="回放截止日">
              <el-date-picker
                v-model="trainingEndDate"
                type="date"
                value-format="YYYY-MM-DD"
                format="YYYY-MM-DD"
                placeholder="选择回放截止日"
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

        <el-card v-if="archiveSessions.length" class="panel-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>训练存档</span>
              <el-tag type="success" effect="light">{{ archiveSessions.length }} 个</el-tag>
            </div>
          </template>

          <el-scrollbar max-height="320px">
            <div
              v-for="archive in archiveSessions"
              :key="archive.session_id"
              class="archive-item"
            >
              <div class="archive-main">
                <strong>{{ archive.symbol_name || archive.symbol }}</strong>
                <span>{{ archive.session_id }}</span>
                <span>{{ archive.start_date }} → {{ archive.end_date || '进行中' }}</span>
              </div>
              <div class="archive-meta">
                <span>步数 {{ archive.current_step }}/{{ archive.total_days }}</span>
                <span>总资产 ¥{{ formatMoney(archive.total_equity) }}</span>
                <span v-if="archive.score != null">评分 {{ formatScore(archive.score) }}</span>
                <span>{{ archive.status === 'finished' ? '已结束' : '进行中' }}</span>
              </div>
              <el-button size="small" type="primary" @click="resumeArchive(archive.session_id)">
                继续
              </el-button>
            </div>
          </el-scrollbar>
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
              <span>回溯起点</span>
              <strong>{{ session.start_date }}</strong>
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

          <div v-if="step?.visible_bars?.length" class="chart-panel" data-chart-build="2026-07-06">
            <div class="chart-toolbar">
              <el-tag type="success" effect="light">K线 / MA / MACD / 成交量</el-tag>
              <span class="chart-meta">已回放 {{ step.visible_bars.length }} 根</span>
            </div>

            <div ref="chartRef" class="training-chart"></div>

            <el-table
              :data="step.visible_bars"
              style="width: 100%"
              height="240"
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
          </div>

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
            <el-col :xs="12" :sm="8" :md="6">
              <div class="metric-box">
                <span>综合评分</span>
                <strong :class="scoreClass(report.score)">{{ formatScore(report.score) }}</strong>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { use as echartsUse } from 'echarts/core'
import { CandlestickChart, LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import { favoritesApi } from '@/api/favorites'
import { etfsApi } from '@/api/etfs'
import { trainingApi, type TrainingAdvice, type TrainingReport, type TrainingReplayStep, type TrainingSessionResponse, type TrainingSessionSummary } from '@/api/training'

echartsUse([CandlestickChart, LineChart, BarChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, TitleComponent, CanvasRenderer])

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
const trainingEndDate = ref(getTodayDate())
const initialCash = ref(100000)
const totalDays = ref(30)
const note = ref('')
const creating = ref(false)
const submitting = ref(false)
const finishing = ref(false)

const stockOptions = ref<StockOption[]>([])
const etfOptions = ref<EtfOption[]>([])
const chartRef = ref<HTMLDivElement | null>(null)

const session = ref<TrainingSessionResponse | null>(null)
const step = ref<TrainingReplayStep | null>(null)
const report = ref<TrainingReport | null>(null)
const advice = ref<TrainingAdvice | null>(null)
const archiveSessions = ref<TrainingSessionSummary[]>([])

const tradeSide = ref<'buy' | 'sell'>('buy')
const tradeQuantity = ref(100)

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
const latestArchive = computed(() => archiveSessions.value[0] || null)

const overviewRows = computed(() => {
  const currentSessionLabel = session.value
    ? `${session.value.session_id} · ${session.value.current_step}/${session.value.total_days}`
    : `等待创建 · ${totalDays.value} 个交易日`
  const currentSessionNote = session.value
    ? `${session.value.symbol_name || session.value.symbol} · ${session.value.status === 'finished' ? '已结束' : '进行中'}`
    : '请先选择股票或 ETF，然后点击“新建存档”'

  const archiveLabel = `${archiveSessions.value.length} 个`
  const archiveNote = latestArchive.value
    ? `${latestArchive.value.symbol_name || latestArchive.value.symbol} · ${latestArchive.value.session_id} · ${latestArchive.value.status === 'finished' ? '已结束' : '进行中'}`
    : '暂无历史存档'

  const comparisonLabel = report.value
    ? `${formatPercent(report.value.active_return)} / ${formatPercent(report.value.buy_and_hold_return)}`
    : '等待训练结束'
  const comparisonNote = report.value
    ? `超额收益 ${formatPercent(report.value.excess_return)}`
    : '主动做 T 和买入持有的对比会在赛后自动生成'

  const scoreLabel = report.value ? `${formatScore(report.value.score)} 分` : '100 分基准'
  const scoreNote = report.value
    ? '与买入持有持平为 100 分，超额收益越高分数越高'
    : '训练结束后生成综合评分'

  return [
    { label: '当前会话', value: currentSessionLabel, note: currentSessionNote },
    { label: '历史存档', value: archiveLabel, note: archiveNote },
    { label: '收益对比', value: comparisonLabel, note: comparisonNote },
    { label: '综合评分', value: scoreLabel, note: scoreNote },
  ]
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

function getTodayDate() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
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

function scoreClass(value: unknown) {
  const num = Number(value ?? 0)
  if (!Number.isFinite(num)) {
    return ''
  }
  if (num > 100) return 'positive'
  if (num < 100) return 'negative'
  return ''
}

function formatScore(value: unknown) {
  const num = Number(value ?? NaN)
  return Number.isFinite(num) ? num.toFixed(2) : '-'
}

function average(values: number[]) {
  if (values.length === 0) {
    return null
  }
  const sum = values.reduce((acc, value) => acc + value, 0)
  return sum / values.length
}

function buildMa(values: number[], period: number) {
  return values.map((_, index) => {
    if (index < period - 1) {
      return null
    }
    return average(values.slice(index - period + 1, index + 1))
  })
}

function buildEma(values: number[], period: number) {
  const result: Array<number | null> = []
  const multiplier = 2 / (period + 1)
  values.forEach((value, index) => {
    if (index === 0) {
      result.push(value)
      return
    }
    const prev = result[index - 1]
    if (prev == null) {
      result.push(value)
      return
    }
    result.push((value - prev) * multiplier + prev)
  })
  return result
}

function buildMacd(values: number[]) {
  const ema12 = buildEma(values, 12)
  const ema26 = buildEma(values, 26)
  const dif = values.map((_, index) => {
    const a = ema12[index]
    const b = ema26[index]
    if (a == null || b == null) {
      return null
    }
    return a - b
  })
  const dea = buildEma(dif.map((value) => value ?? 0), 9)
  const hist = dif.map((value, index) => {
    const a = value
    const b = dea[index]
    if (a == null || b == null) {
      return null
    }
    return (a - b) * 2
  })
  return { dif, dea, hist }
}

const chartBars = computed(() => {
  const bars = step.value?.visible_bars || []
  return bars
    .map((bar) => ({
      trade_date: bar.trade_date,
      open: Number(bar.open ?? NaN),
      high: Number(bar.high ?? NaN),
      low: Number(bar.low ?? NaN),
      close: Number(bar.close ?? NaN),
      volume: Number(bar.volume ?? NaN)
    }))
    .filter((bar) => Number.isFinite(bar.open) && Number.isFinite(bar.high) && Number.isFinite(bar.low) && Number.isFinite(bar.close))
})

const chartOption = computed<EChartsOption>(() => {
  const bars = chartBars.value
  const categories = bars.map((bar) => bar.trade_date)
  const candleData = bars.map((bar) => [bar.open, bar.close, bar.low, bar.high])
  const closes = bars.map((bar) => bar.close)
  const ma5 = buildMa(closes, 5)
  const ma10 = buildMa(closes, 10)
  const ma20 = buildMa(closes, 20)
  const macd = buildMacd(closes)
  const volumeData = bars.map((bar, index) => {
    const prevClose = index > 0 ? bars[index - 1]?.close : bar.open
    const rising = bar.close >= (prevClose ?? bar.open)
    return {
      value: bar.volume || 0,
      itemStyle: { color: rising ? '#ef4444' : '#22c55e' }
    }
  })

  return {
    animation: false,
    legend: {
      top: 4,
      left: 'center',
      textStyle: { color: '#94a3b8' },
      data: ['K线', 'MA5', 'MA10', 'MA20', 'DIF', 'DEA', 'MACD', '成交量']
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }]
    },
    grid: [
      { left: 50, right: 20, top: 48, height: '48%' },
      { left: 50, right: 20, top: '60%', height: '17%' },
      { left: 50, right: 20, top: '80%', height: '14%' }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1, 2], start: 55, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1, 2], top: '96%', height: 18, start: 55, end: 100 }
    ],
    xAxis: [
      {
        type: 'category',
        data: categories,
        boundaryGap: true,
        axisLine: { onZero: false },
        axisLabel: { show: false },
        splitLine: { show: false },
        gridIndex: 0
      },
      {
        type: 'category',
        data: categories,
        boundaryGap: true,
        axisLine: { onZero: false },
        axisLabel: { show: false },
        splitLine: { show: false },
        gridIndex: 1
      },
      {
        type: 'category',
        data: categories,
        boundaryGap: true,
        axisLine: { onZero: false },
        axisLabel: { color: '#94a3b8' },
        splitLine: { show: false },
        gridIndex: 2
      }
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        splitArea: { show: true },
        axisLabel: { color: '#94a3b8' }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 4,
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.16)' } }
      },
      {
        scale: true,
        gridIndex: 2,
        splitNumber: 3,
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.16)' } }
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: candleData,
        itemStyle: {
          color: '#ef4444',
          color0: '#22c55e',
          borderColor: '#ef4444',
          borderColor0: '#22c55e'
        }
      },
      {
        name: 'MA5',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma5,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#f59e0b' }
      },
      {
        name: 'MA10',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma10,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#60a5fa' }
      },
      {
        name: 'MA20',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma20,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#a78bfa' }
      },
      {
        name: 'DIF',
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: macd.dif,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.1, color: '#f59e0b' }
      },
      {
        name: 'DEA',
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: macd.dea,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.1, color: '#60a5fa' }
      },
      {
        name: 'MACD',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: macd.hist.map((value) => ({
          value: value ?? 0,
          itemStyle: { color: (value ?? 0) >= 0 ? '#ef4444' : '#22c55e' }
        })),
        barWidth: '55%'
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: volumeData,
        barWidth: '55%'
      }
    ]
  }
})

let chartInstance: echarts.ECharts | null = null

async function renderChart() {
  await nextTick()
  if (!chartRef.value) {
    return
  }
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  chartInstance.setOption(chartOption.value, true)
}

function resizeChart() {
  chartInstance?.resize()
}

function disposeChart() {
  chartInstance?.dispose()
  chartInstance = null
}

function normalizeStockOption(item: any): StockOption | null {
  const symbol = item?.symbol || item?.stock_code
  const name = item?.stock_name || item?.name
  if (!symbol || !name) {
    return null
  }
  return {
    symbol,
    name,
    market: item?.market
  }
}

function normalizeEtfOption(item: any): EtfOption | null {
  const fundCode = item?.fund_code || item?.symbol
  const fundName = item?.fund_name || item?.name
  if (!fundCode || !fundName) {
    return null
  }
  return {
    fund_code: fundCode,
    fund_name: fundName,
    fund_type: item?.fund_type || ''
  }
}

async function loadEtfOptions() {
  if (etfOptions.value.length > 0) {
    return
  }
  try {
    const res = await etfsApi.list()
    const list = Array.isArray(res.data) ? res.data : []
    etfOptions.value = list.map(normalizeEtfOption).filter(Boolean) as EtfOption[]
    if (!selectedSymbol.value && instrumentType.value === 'etf') {
      selectedSymbol.value = etfOptions.value[0]?.fund_code || ''
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '加载 ETF 列表失败')
  }
}

async function loadStockOptions() {
  if (stockOptions.value.length > 0) {
    return
  }
  try {
    const res = await favoritesApi.list()
    const list = Array.isArray(res.data) ? res.data : []
    stockOptions.value = list.map(normalizeStockOption).filter(Boolean) as StockOption[]
    if (!selectedSymbol.value && instrumentType.value === 'stock') {
      selectedSymbol.value = stockOptions.value[0]?.symbol || ''
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '加载自选股票失败')
  }
}

async function loadTrainingOptions() {
  await Promise.all([loadStockOptions(), loadEtfOptions()])
}

async function loadArchiveSessions() {
  try {
    const res = await trainingApi.listSessions({ skipErrorHandler: true })
    archiveSessions.value = Array.isArray(res.data) ? res.data : []
  } catch (error: any) {
    archiveSessions.value = []
    if (error?.response?.status !== 404) {
      ElMessage.error(error?.message || '加载训练存档失败')
    }
  }
}

async function resumeArchive(sessionId: string) {
  if (!sessionId) {
    return
  }
  await router.replace({ path: '/training', query: { sessionId } })
  await loadSession(sessionId)
}

function resolveSelectedSymbol() {
  if (selectedSymbol.value) {
    return selectedSymbol.value
  }
  if (instrumentType.value === 'stock') {
    return stockOptions.value[0]?.symbol || etfOptions.value[0]?.fund_code || ''
  }
  return etfOptions.value[0]?.fund_code || stockOptions.value[0]?.symbol || ''
}

function onInstrumentTypeChange() {
  selectedSymbol.value = ''
  if (instrumentType.value === 'etf') {
    void loadEtfOptions()
  } else {
    void loadStockOptions()
  }
}

async function loadStep(sessionId: string) {
  try {
    const res = await trainingApi.getStep(sessionId, { skipErrorHandler: true })
    step.value = res.data
    advice.value = res.data?.advice || null
    if (res.data?.session) {
      session.value = res.data.session
    }
  } catch (error: any) {
    if (error?.response?.status === 404) {
      await resetTrainingContext()
      return
    }
    throw error
  }
}

async function loadSession(sessionId: string) {
  try {
    const res = await trainingApi.getSession(sessionId, { skipErrorHandler: true })
    session.value = res.data
    if (res.data.status === 'finished') {
      const reportRes = await trainingApi.getReport(sessionId, { skipErrorHandler: true })
      report.value = reportRes.data
    }
    await loadStep(sessionId)
  } catch (error: any) {
    if (error?.response?.status === 404) {
      await resetTrainingContext()
      return
    }
    throw error
  }
}

async function resetTrainingContext() {
  session.value = null
  step.value = null
  report.value = null
  advice.value = null
  await router.replace({ path: '/training' })
  await loadArchiveSessions()
}

async function createTraining() {
  if (!trainingEndDate.value) {
    ElMessage.warning('请先选择回放截止日')
    return
  }

  creating.value = true
  try {
    await loadTrainingOptions()
    const symbol = resolveSelectedSymbol()
    if (!symbol) {
      ElMessage.warning('请先在自选股票或 ETF 中至少加入一个标的')
      return
    }
    selectedSymbol.value = symbol

    const res = await trainingApi.createSession({
      symbol,
      end_date: trainingEndDate.value,
      initial_cash: initialCash.value,
      total_days: totalDays.value,
      market: 'CN',
      note: note.value || undefined,
    })
    session.value = res.data
    report.value = null
    await router.replace({ path: '/training', query: { sessionId: res.data.session_id } })
    await loadStep(res.data.session_id)
    await loadArchiveSessions()
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
    await loadArchiveSessions()
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
        if (error?.response?.status === 404) {
          await resetTrainingContext()
          return
        }
        ElMessage.error(error?.message || '恢复训练会话失败')
      }
    }
  },
  { immediate: true }
)

onMounted(() => {
  void loadTrainingOptions()
  void loadArchiveSessions()
  void renderChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  disposeChart()
})

watch(
  chartOption,
  () => {
    void renderChart()
  },
  { deep: true }
)
</script>

<style scoped lang="scss">
.training-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: var(--glass-shadow-sm);
}

.overview-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.overview-copy {
  max-width: 760px;

  h1 {
    margin: 10px 0 12px;
    font-size: 28px;
    line-height: 1.15;
  }

  p {
    margin: 0;
    color: var(--el-text-color-secondary);
    line-height: 1.7;
    max-width: 720px;
  }
}

.overview-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 13px;
  letter-spacing: 0.08em;
}

.overview-actions {
  display: grid;
  gap: 10px;
  min-width: 260px;
}

.overview-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
}

.overview-chip span {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.overview-chip strong {
  font-size: 14px;
}

.overview-table {
  width: 100%;

  :deep(.el-table__cell) {
    background: transparent;
  }

  :deep(.el-table__row:hover > td) {
    background: rgba(15, 118, 110, 0.03) !important;
  }
}

.overview-note {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.training-grid {
  align-items: flex-start;
}

.panel-card {
  margin-bottom: 20px;
  border-radius: 18px;
}

.chart-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chart-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.training-chart {
  width: 100%;
  height: 560px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.6), rgba(241, 245, 249, 0.88));
  border: 1px solid var(--el-border-color-lighter);
}

.archive-item {
  display: grid;
  gap: 8px;
  padding: 14px;
  margin-bottom: 12px;
  border-radius: 14px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
}

.archive-main,
.archive-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  align-items: center;
}

.archive-main strong {
  font-size: 14px;
}

.archive-main span,
.archive-meta span {
  font-size: 12px;
  color: var(--el-text-color-secondary);
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

  .chart-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .training-chart {
    height: 420px;
  }
}
</style>
