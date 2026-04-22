<template>
  <div class="page-container">
    <!-- Header -->
    <div class="page-header">
      <h1>古典音乐</h1>
      <div class="header-actions">
        <button class="btn-wood" @click="router.push('/search')">🔍 搜索</button>
        <button class="btn-wood" v-if="authStore.user?.role === 'admin'" @click="router.push('/admin')">⚙️ 管理</button>
        <button class="btn-wood" @click="authStore.logout(); router.push('/login')">退出</button>
      </div>
    </div>

    <!-- Search bar -->
    <div class="skeuo-inset search-bar">
      <input
        v-model="searchQuery"
        type="text"
        class="skeuo-input"
        placeholder="搜索作曲家、曲目..."
        @keyup.enter="doSearch"
      />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-text">加载中...</div>

    <!-- Browse by Era -->
    <div v-else class="grid-era">
      <div v-for="era in eras" :key="era.name" class="era-section">
        <div class="era-header">
          <h2>{{ era.name }}</h2>
          <span class="era-badge">{{ era.period }}</span>
        </div>
        <div class="grid-composers">
          <div
            v-for="work in era.works"
            :key="work.id"
            class="composer-card"
            @click="router.push(`/work/${work.id}`)"
          >
            <div class="composer-avatar">{{ work.composer[0] }}</div>
            <div>
              <div style="font-weight: 600; font-size: 0.9rem;">{{ work.title }}</div>
              <div style="font-size: 0.78rem; color: var(--text-muted);">{{ work.composer }}</div>
              <div v-if="work.catalog_number" style="font-size: 0.7rem; color: var(--text-muted);">{{ work.catalog_number }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- No works -->
      <div v-if="eras.length === 0 && !loading" class="empty-state skeuo-panel">
        <p>🎵 音乐库为空</p>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem;">
          请在管理面板中扫描音乐目录
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getWorks } from '@/api'
import type { Work } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

const allWorks = ref<Work[]>([])
const loading = ref(true)
const searchQuery = ref('')

const ERA_ORDER = ['文艺复兴', '巴洛克', '古典', '浪漫', '民族乐派', '印象主义', '现代', '后现代', '当代']
const ERA_PERIODS: Record<string, string> = {
  '文艺复兴': '1400–1600',
  '巴洛克': '1600–1750',
  '古典': '1750–1820',
  '浪漫': '1820–1910',
  '民族乐派': '1850–1920',
  '印象主义': '1875–1925',
  '现代': '1900–1975',
  '后现代': '1960–',
  '当代': '1975–',
}

const eras = computed(() => {
  const grouped: Record<string, Work[]> = {}
  for (const w of allWorks.value) {
    const era = w.era || '其他'
    if (!grouped[era]) grouped[era] = []
    grouped[era].push(w)
  }
  return ERA_ORDER
    .filter(e => grouped[e]?.length)
    .map(e => ({ name: e, period: ERA_PERIODS[e] || '', works: grouped[e] }))
    .concat(
      grouped['其他']?.length
        ? [{ name: '其他', period: '', works: grouped['其他'] }]
        : []
    )
})

function doSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/search', query: { q: searchQuery.value } })
  }
}

onMounted(async () => {
  try {
    const data = await getWorks({ limit: 100 })
    allWorks.value = data.items
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 0.5rem;
}

.search-bar {
  margin-bottom: 1.25rem;
}

.era-section {
  margin-bottom: 0.5rem;
}

.era-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-groove);
}

.loading-text {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

.empty-state {
  text-align: center;
  padding: 3rem;
  font-size: 1.1rem;
}
</style>
