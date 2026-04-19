<template>
  <div class="page-container">
    <button class="btn-wood" @click="router.back()">← 返回</button>

    <h1 style="margin: 1rem 0 0.75rem;">⚙️ 系统管理</h1>

    <!-- Scan Section -->
    <div class="skeuo-panel" style="margin-bottom: 1rem;">
      <h2>音乐库扫描</h2>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0.5rem 0;">
        扫描音乐目录，提取元数据并建立索引
      </p>

      <div class="scan-controls">
        <button class="btn-gold" @click="startScan" :disabled="scanning">
          {{ scanning ? '扫描中...' : '开始扫描' }}
        </button>
        <button class="btn-wood" @click="refreshStatus">刷新状态</button>
      </div>

      <!-- Scan Progress -->
      <div v-if="scanStatus" class="skeuo-inset scan-status" style="margin-top: 1rem;">
        <div class="status-row">
          <span>状态:</span>
          <span :class="statusClass">{{ statusLabel }}</span>
        </div>
        <div class="status-row" v-if="scanStatus.total > 0">
          <span>进度:</span>
          <span>{{ scanStatus.current }} / {{ scanStatus.total }}</span>
        </div>
        <div v-if="scanStatus.total > 0" class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div v-if="scanStatus.message" class="status-message">
          {{ scanStatus.message }}
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="skeuo-panel">
      <h2>音乐库统计</h2>
      <div class="stats-grid" style="margin-top: 0.75rem;">
        <div class="stat-item skeuo-inset">
          <div class="stat-value">{{ stats.works }}</div>
          <div class="stat-label">曲目</div>
        </div>
        <div class="stat-item skeuo-inset">
          <div class="stat-value">{{ stats.composers }}</div>
          <div class="stat-label">作曲家</div>
        </div>
        <div class="stat-item skeuo-inset">
          <div class="stat-value">{{ stats.movements }}</div>
          <div class="stat-label">乐章</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { triggerScan, getScanStatus, getWorks } from '@/api'
import type { ScanStatus } from '@/types'

const router = useRouter()

const scanStatus = ref<ScanStatus | null>(null)
const scanning = ref(false)
const stats = ref({ works: 0, composers: 0, movements: 0 })
let pollTimer: ReturnType<typeof setInterval> | null = null

const progressPercent = computed(() => {
  if (!scanStatus.value || !scanStatus.value.total) return 0
  return Math.round((scanStatus.value.current / scanStatus.value.total) * 100)
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    idle: '空闲',
    pending: '等待中',
    running: '扫描中',
    completed: '已完成',
    failed: '失败',
  }
  return map[scanStatus.value?.status || 'idle'] || scanStatus.value?.status || '空闲'
})

const statusClass = computed(() => {
  const s = scanStatus.value?.status
  if (s === 'completed') return 'status-ok'
  if (s === 'running') return 'status-running'
  if (s === 'failed') return 'status-error'
  return ''
})

async function startScan() {
  scanning.value = true
  try {
    await triggerScan()
    startPolling()
  } catch (e: any) {
    console.error(e)
  }
}

async function refreshStatus() {
  try {
    scanStatus.value = await getScanStatus()
    if (scanStatus.value.status === 'running') {
      scanning.value = true
      startPolling()
    } else {
      scanning.value = false
      stopPolling()
    }
  } catch (e) {
    console.error(e)
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      scanStatus.value = await getScanStatus()
      if (scanStatus.value.status !== 'running') {
        scanning.value = false
        stopPolling()
        loadStats()
      }
    } catch {
      stopPolling()
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadStats() {
  try {
    const data = await getWorks({ limit: 1 })
    stats.value.works = data.total

    // Approximate composers count from browsing
    const allData = await getWorks({ limit: 100 })
    const composers = new Set(allData.items.map(w => w.composer))
    stats.value.composers = composers.size
    stats.value.movements = allData.items.reduce((sum, w) => sum + w.movement_count, 0)
  } catch {}
}

onMounted(() => {
  refreshStatus()
  loadStats()
})
</script>

<style scoped>
.scan-controls {
  display: flex;
  gap: 0.5rem;
}

.scan-status { }

.status-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  margin-bottom: 0.4rem;
}

.status-ok { color: #81c784; }
.status-running { color: var(--accent-gold); }
.status-error { color: #e57373; }

.progress-bar {
  height: 8px;
  background: var(--bg-dark);
  border-radius: 4px;
  overflow: hidden;
  margin: 0.5rem 0;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-gold) 0%, var(--accent-warm) 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.status-message {
  font-size: 0.8rem;
  color: var(--text-muted);
  word-break: break-all;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--accent-gold);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

@media (max-width: 600px) {
  .stats-grid { grid-template-columns: 1fr; }
}
</style>
