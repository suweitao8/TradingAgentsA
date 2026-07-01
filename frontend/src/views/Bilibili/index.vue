<template>
  <div class="bilibili-page">
    <!-- 股票/ETF/B站 切换 Tab -->
    <WatchlistTabs active="bilibili" />

    <!-- 操作栏 -->
    <el-card class="action-card" shadow="never">
      <div class="action-bar">
        <div class="action-buttons">
          <el-button @click="loadData" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button type="success" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加 UP 主
          </el-button>
        </div>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索 UP 主名称或 UID"
          clearable
          class="search-input"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </el-card>

    <!-- UP 主列表 -->
    <el-card class="list-card" shadow="never">
      <el-table
        :data="filteredUpmasters"
        v-loading="loading"
        style="width: 100%"
        row-key="mid"
        :expand-row-keys="expandedKeys"
        @expand-change="onExpandChange"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <!-- 股票观点表 -->
              <div v-if="row.stocks && row.stocks.length > 0" class="stocks-section">
                <h4 class="section-title">📈 提及的股票观点（LLM 提取）</h4>
                <el-table :data="row.stocks" size="small" border>
                  <el-table-column label="股票" prop="stock_name" min-width="100" />
                  <el-table-column label="代码" prop="stock_code" width="90">
                    <template #default="{ row: s }">
                      <span v-if="s.stock_code">{{ s.stock_code }}</span>
                      <span v-else style="color: var(--glass-text-tertiary);">-</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="观点" width="80">
                    <template #default="{ row: s }">
                      <el-tag :type="sentimentTag(s.sentiment)" size="small">{{ s.sentiment }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="原文摘录" prop="mention" min-width="200" show-overflow-tooltip />
                  <el-table-column label="时间" prop="pub_time" width="130" />
                </el-table>
              </div>
              <el-empty v-else description="未提取到股票观点" :image-size="60" />

              <!-- 动态列表 -->
              <div v-if="row.dynamics && row.dynamics.length > 0" class="dynamics-section">
                <h4 class="section-title">📰 最新动态</h4>
                <div class="dynamic-list">
                  <div v-for="d in row.dynamics" :key="d.id" class="dynamic-item">
                    <div class="dynamic-header">
                      <span class="dynamic-time">{{ d.pub_time }}</span>
                      <el-tag size="small" :type="dynTypeTag(d.type)">{{ dynTypeLabel(d.type) }}</el-tag>
                    </div>
                    <div v-if="d.title" class="dynamic-title">{{ d.title }}</div>
                    <div v-if="d.text" class="dynamic-text">{{ d.text }}</div>
                  </div>
                </div>
              </div>

              <!-- 抓取错误 -->
              <el-alert v-if="row.fetch_error" type="error" :title="`抓取失败: ${row.fetch_error}`" :closable="false" show-icon style="margin-top: 12px;" />
            </div>
          </template>
        </el-table-column>

        <el-table-column type="index" label="#" width="55" align="center" />
        <el-table-column label="UP 主" min-width="180">
          <template #default="{ row }">
            <span class="up-name">{{ row.uname }}</span>
            <span class="up-mid">{{ row.mid }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
            <span v-else style="color: var(--glass-text-tertiary);">-</span>
          </template>
        </el-table-column>
        <el-table-column label="提及股票" width="120">
          <template #default="{ row }">
            <el-badge :value="row.stocks?.length || 0" :hidden="!row.stocks?.length" type="primary">
              <span class="stock-count">{{ row.stocks?.length || 0 }} 只</span>
            </el-badge>
          </template>
        </el-table-column>
        <el-table-column label="最新动态" min-width="250">
          <template #default="{ row }">
            <span v-if="row.dynamics && row.dynamics.length > 0" class="latest-dyn">
              {{ (row.dynamics[0].title || row.dynamics[0].text || '').slice(0, 50) }}
            </span>
            <span v-else style="color: var(--glass-text-tertiary);">暂无</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewUpSpace(row)">主页</el-button>
            <el-button type="danger" link size="small" @click="removeUp(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && upmasters.length === 0" class="empty-state">
        <el-empty description="还没有添加 B 站 UP 主">
          <el-button type="primary" @click="showAddDialog">添加 UP 主</el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 添加 UP 主对话框 -->
    <el-dialog v-model="addDialogVisible" title="添加 B 站 UP 主" width="520px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="UP 主 UID">
          <el-input v-model="addForm.mid" placeholder="输入 B 站 UID（如 3706942109256376）" @blur="previewUp" />
        </el-form-item>
        <el-form-item v-if="previewInfo" label="预览">
          <div class="preview-box">
            <img v-if="previewInfo.face" :src="previewInfo.face" class="preview-face" />
            <div>
              <div class="preview-name">{{ previewInfo.uname }}</div>
              <div class="preview-sign">{{ previewInfo.sign || '暂无签名' }}</div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="addForm.uname" placeholder="UP 主名称（留空自动获取）" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="addForm.category" placeholder="选择分类（可选）" clearable>
            <el-option label="股票" value="股票" />
            <el-option label="财经" value="财经" />
            <el-option label="科技" value="科技" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addForm.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="adding">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import WatchlistTabs from '@/components/Layout/WatchlistTabs.vue'
import { bilibiliApi } from '@/api/bilibili'
import type { UpmasterItem, UpmasterSearchResult } from '@/api/bilibili'

const loading = ref(false)
const upmasters = ref<UpmasterItem[]>([])
const searchKeyword = ref('')
const expandedKeys = ref<string[]>([])

const filteredUpmasters = computed(() => {
  if (!searchKeyword.value) return upmasters.value
  const kw = searchKeyword.value.toLowerCase()
  return upmasters.value.filter(
    u => u.uname?.toLowerCase().includes(kw) || u.mid?.includes(kw)
  )
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await bilibiliApi.list()
    upmasters.value = ((res as any)?.data || []) as UpmasterItem[]
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
    upmasters.value = []
  } finally {
    loading.value = false
  }
}

const onExpandChange = (row: UpmasterItem, expanded: UpmasterItem[]) => {
  expandedKeys.value = expanded.map(r => r.mid)
}

// 添加 UP 主
const addDialogVisible = ref(false)
const adding = ref(false)
const addForm = ref({ mid: '', uname: '', category: '', notes: '' })
const previewInfo = ref<UpmasterSearchResult | null>(null)

const showAddDialog = () => {
  addForm.value = { mid: '', uname: '', category: '', notes: '' }
  previewInfo.value = null
  addDialogVisible.value = true
}

const previewUp = async () => {
  if (!addForm.value.mid || previewInfo.value?.mid === addForm.value.mid) return
  try {
    const res = await bilibiliApi.searchUp(addForm.value.mid)
    const info = (res as any)?.data
    if (info) {
      previewInfo.value = info
      if (!addForm.value.uname) addForm.value.uname = info.uname
    }
  } catch {
    previewInfo.value = null
  }
}

const handleAdd = async () => {
  if (!addForm.value.mid) {
    ElMessage.warning('请输入 UP 主 UID')
    return
  }
  adding.value = true
  try {
    await bilibiliApi.add({
      mid: addForm.value.mid,
      uname: addForm.value.uname,
      category: addForm.value.category,
      notes: addForm.value.notes,
    })
    ElMessage.success('添加成功')
    addDialogVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.message || '添加失败')
  } finally {
    adding.value = false
  }
}

const removeUp = async (row: UpmasterItem) => {
  try {
    await ElMessageBox.confirm(`确定移除 UP 主「${row.uname}」？`, '确认', { type: 'warning' })
    await bilibiliApi.remove(row.mid)
    ElMessage.success('已移除')
    await loadData()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.message || '移除失败')
  }
}

const viewUpSpace = (row: UpmasterItem) => {
  window.open(`https://space.bilibili.com/${row.mid}/dynamic`, '_blank')
}

const sentimentTag = (s: string) => {
  if (/多|买入/.test(s)) return 'success'
  if (/空|卖出/.test(s)) return 'danger'
  if (/观望/.test(s)) return 'warning'
  return 'info'
}

const dynTypeLabel = (t: string) => {
  const m: Record<string, string> = {
    DYNAMIC_TYPE_AV: '视频',
    DYNAMIC_TYPE_WORD: '文字',
    DYNAMIC_TYPE_DRAW: '图文',
    DYNAMIC_TYPE_FORWARD: '转发',
    DYNAMIC_TYPE_ARTICLE: '专栏',
  }
  return m[t] || '动态'
}
const dynTypeTag = (t: string) => {
  if (t === 'DYNAMIC_TYPE_AV') return ''
  if (t === 'DYNAMIC_TYPE_DRAW') return 'warning'
  return 'info'
}

onMounted(loadData)
</script>

<style scoped>
.bilibili-page { padding: 16px; }
.action-card { margin-bottom: 16px; }
.action-bar { display: flex; justify-content: space-between; align-items: center; }
.action-buttons { display: flex; gap: 8px; }
.search-input { width: 260px; }

.up-name { font-weight: 600; margin-right: 8px; }
.up-mid { color: var(--glass-text-tertiary); font-size: 12px; }
.stock-count { font-size: 13px; color: var(--glass-text-secondary); }
.latest-dyn { color: var(--glass-text-secondary); font-size: 13px; }

.expand-content { padding: 12px 24px; background: var(--glass-bg-surface); }
.section-title { margin: 16px 0 8px; font-size: 14px; color: var(--glass-text-primary); }
.stocks-section { margin-bottom: 20px; }

.dynamic-list { display: flex; flex-direction: column; gap: 12px; }
.dynamic-item {
  padding: 10px 14px;
  background: var(--glass-bg-base);
  border-radius: 8px;
  border-left: 3px solid var(--accent-cyan);
}
.dynamic-header { display: flex; gap: 8px; align-items: center; margin-bottom: 4px; }
.dynamic-time { font-size: 12px; color: var(--glass-text-tertiary); }
.dynamic-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.dynamic-text { font-size: 13px; color: var(--glass-text-secondary); white-space: pre-wrap; line-height: 1.6; }

.preview-box { display: flex; gap: 12px; align-items: center; }
.preview-face { width: 48px; height: 48px; border-radius: 50%; }
.preview-name { font-weight: 600; }
.preview-sign { font-size: 12px; color: var(--glass-text-tertiary); max-width: 300px; }

.empty-state { padding: 40px 0; }
</style>
