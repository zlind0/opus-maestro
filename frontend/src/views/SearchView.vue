<template>
  <div class="page-container">
    <button class="btn-wood" @click="router.back()">← 返回</button>

    <h1 style="margin: 1rem 0 0.75rem;">搜索</h1>

    <div class="skeuo-inset" style="margin-bottom: 1rem;">
      <input
        v-model="query"
        type="text"
        class="skeuo-input"
        placeholder="输入作曲家、曲名、情绪..."
        @keyup.enter="doSearch"
        autofocus
      />
    </div>

    <!-- Filters -->
    <div class="filter-row">
      <select v-model="filterEra" class="skeuo-input filter-select">
        <option value="">全部年代</option>
        <option v-for="e in eraOptions" :key="e" :value="e">{{ e }}</option>
      </select>
      <select v-model="filterType" class="skeuo-input filter-select">
        <option value="">全部类型</option>
        <option v-for="t in typeOptions" :key="t" :value="t">{{ t }}</option>
      </select>
      <button class="btn-gold" @click="doSearch">搜索</button>
    </div>

    <!-- Results -->
    <div v-if="searching" class="loading-text">搜索中...</div>

    <div v-else-if="results.length > 0">
      <div class="result-type" v-if="resultType">
        {{ resultType === 'semantic' ? '🤖 语义搜索结果' : '🔍 精确搜索结果' }}
      </div>
      <div class="grid-composers">
        <div
          v-for="work in results"
          :key="work.id"
          class="composer-card"
          @click="router.push(`/work/${work.id}`)"
        >
          <div class="composer-avatar">{{ work.composer[0] }}</div>
          <div>
            <div style="font-weight: 600; font-size: 0.9rem;">{{ work.title }}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">{{ work.composer }}</div>
            <div v-if="work.era" style="font-size: 0.7rem; color: var(--text-muted);">{{ work.era }} · {{ work.work_type }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="searched" class="empty-state skeuo-panel">
      <p>未找到相关结果</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { search } from '@/api'
import type { Work } from '@/types'

const route = useRoute()
const router = useRouter()

const query = ref((route.query.q as string) || '')
const filterEra = ref('')
const filterType = ref('')
const results = ref<Work[]>([])
const resultType = ref('')
const searching = ref(false)
const searched = ref(false)

const eraOptions = ['文艺复兴', '巴洛克', '古典', '浪漫', '民族乐派', '印象主义', '现代', '后现代', '当代']
const typeOptions = ['交响曲', '协奏曲', '奏鸣曲', '室内乐', '歌剧', '合唱', '独奏曲', '序曲', '变奏曲', '组曲']

async function doSearch() {
  searching.value = true
  searched.value = false
  try {
    const data = await search({
      query: query.value || undefined,
      era: filterEra.value || undefined,
      work_type: filterType.value || undefined,
      limit: 50,
    })
    results.value = data.results
    resultType.value = data.type
    searched.value = true
  } catch (e) {
    console.error(e)
  } finally {
    searching.value = false
  }
}

onMounted(() => {
  if (query.value) doSearch()
})
</script>

<style scoped>
.filter-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.filter-select {
  max-width: 160px;
}
.result-type {
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}
.loading-text { text-align: center; padding: 3rem; color: var(--text-muted); }
.empty-state { text-align: center; padding: 2rem; }

@media (max-width: 600px) {
  .filter-row { flex-wrap: wrap; }
  .filter-select { max-width: none; flex: 1; }
}
</style>
