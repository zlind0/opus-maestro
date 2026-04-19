<template>
  <div class="page-container">
    <button class="btn-wood back-btn" @click="router.back()">← 返回</button>

    <div v-if="loading" class="loading-text">加载中...</div>

    <template v-else-if="work">
      <!-- Work header -->
      <div class="skeuo-panel work-header">
        <div class="work-meta">
          <span class="era-badge" v-if="work.era">{{ work.era }}</span>
          <span class="era-badge" v-if="work.work_type">{{ work.work_type }}</span>
        </div>
        <h1>{{ work.title }}</h1>
        <h3>{{ work.composer }}</h3>
        <div v-if="work.catalog_number" class="catalog">{{ work.catalog_number }}</div>
        <p v-if="work.summary" class="work-summary">{{ work.summary }}</p>
      </div>

      <!-- Versions -->
      <div v-if="versions.length > 1" class="versions-section">
        <h3 style="margin-bottom: 0.5rem;">录音版本</h3>
        <div class="skeuo-inset">
          <div
            v-for="v in versions"
            :key="v.id"
            class="version-item"
            :class="{ active: selectedVersionId === v.id }"
            @click="selectVersion(v.id)"
          >
            <div>{{ v.conductor || '未知指挥' }} · {{ v.ensemble || '未知乐团' }}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">
              {{ v.year || '' }} {{ v.label ? `· ${v.label}` : '' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Movements -->
      <div class="movements-section">
        <h3 style="margin-bottom: 0.5rem;">乐章 ({{ filteredMovements.length }})</h3>
        <div class="skeuo-inset">
          <div v-if="filteredMovements.length === 0" class="empty-movements">
            暂无乐章信息
          </div>
          <div
            v-for="m in filteredMovements"
            :key="m.id"
            class="movement-item"
            :class="{ playing: player.currentMovement?.id === m.id }"
            @click="playMovement(m)"
          >
            <div class="movement-num">{{ m.movement_number }}</div>
            <div class="movement-info">
              <div class="movement-title">{{ m.title || `第${m.movement_number}乐章` }}</div>
              <div class="movement-mood" v-if="m.mood">{{ moodLabel(m.mood) }}</div>
              <div class="movement-mood" v-if="m.description">{{ m.description }}</div>
            </div>
            <div v-if="player.currentMovement?.id === m.id" class="playing-indicator">
              {{ player.isPlaying ? '▶' : '⏸' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Recommendations -->
      <div v-if="player.recommendations.length > 0" class="recs-section">
        <h3 style="margin-bottom: 0.5rem;">推荐聆听</h3>
        <div class="grid-composers">
          <div
            v-for="rec in player.recommendations"
            :key="rec.id"
            class="composer-card"
            @click="router.push(`/work/${rec.id}`)"
          >
            <div class="composer-avatar">{{ rec.composer[0] }}</div>
            <div>
              <div style="font-weight: 600; font-size: 0.85rem;">{{ rec.title }}</div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">{{ rec.composer }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlayerStore } from '@/stores/player'
import { getWork, getWorkMovements, getWorkVersions } from '@/api'
import type { Work, Movement, Version } from '@/types'

const route = useRoute()
const router = useRouter()
const player = usePlayerStore()

const work = ref<Work | null>(null)
const movements = ref<Movement[]>([])
const versions = ref<Version[]>([])
const selectedVersionId = ref<string | null>(null)
const loading = ref(true)

const MOOD_LABELS: Record<string, string> = {
  joyful: '欢快/明朗',
  melancholic: '悲伤/忧郁',
  agitated: '愤怒/激烈',
  calm: '宁静/沉思',
  mysterious: '神秘/朦胧',
  solemn: '辉煌/庄严',
  playful: '戏谑/轻快',
}

function moodLabel(mood: string) {
  return MOOD_LABELS[mood] || mood
}

const filteredMovements = computed(() => {
  if (!selectedVersionId.value) return movements.value
  return movements.value.filter(m => m.version_id === selectedVersionId.value)
})

function selectVersion(versionId: string) {
  selectedVersionId.value = selectedVersionId.value === versionId ? null : versionId
}

async function playMovement(m: Movement) {
  if (!work.value) return
  player.setQueue(filteredMovements.value, filteredMovements.value.indexOf(m))
  await player.playMovement(work.value, m)
}

onMounted(async () => {
  const id = route.params.id as string
  try {
    const [w, movs, vers] = await Promise.all([
      getWork(id),
      getWorkMovements(id),
      getWorkVersions(id),
    ])
    work.value = w
    movements.value = movs
    versions.value = vers
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.back-btn { margin-bottom: 1rem; }

.work-header { margin-bottom: 1.25rem; }
.work-meta { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.catalog { color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem; }
.work-summary { margin-top: 0.75rem; font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; }

.versions-section { margin-bottom: 1.25rem; }
.version-item {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid rgba(90,58,42,0.3);
  cursor: pointer;
  transition: background 0.15s;
}
.version-item:hover { background: rgba(93,64,55,0.3); }
.version-item:last-child { border-bottom: none; }
.version-item.active {
  background: rgba(201,169,110,0.15);
  border-left: 3px solid var(--accent-gold);
}

.movements-section { margin-bottom: 1.25rem; }
.empty-movements { padding: 2rem; text-align: center; color: var(--text-muted); }

.movement-item.playing {
  background: rgba(201,169,110,0.1);
}
.playing-indicator {
  color: var(--accent-gold);
  font-size: 1rem;
}

.recs-section { margin-top: 1.5rem; }
.loading-text { text-align: center; padding: 3rem; color: var(--text-muted); }
</style>
