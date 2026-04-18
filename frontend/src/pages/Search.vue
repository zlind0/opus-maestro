<template>
  <div class="search-container">
    <div class="search-box">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search classical music... (e.g., Mozart Symphony No. 40)"
        @keyup.enter="handleSearch"
      />
      <button @click="handleSearch" :disabled="isLoading">
        {{ isLoading ? 'Searching...' : 'Search' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="results.length > 0" class="results">
      <h2>{{ results.length }} Result{{ results.length !== 1 ? 's' : '' }}</h2>
      <div class="result-grid">
        <div v-for="work in results" :key="work.work_id" class="result-card">
          <div class="card-header">
            <h3>{{ work.title }}</h3>
            <p class="composer">{{ work.composer }}</p>
          </div>
          <div class="card-body">
            <p><strong>Type:</strong> {{ work.work_type }}</p>
            <p><strong>Catalog:</strong> {{ work.catalog_number }}</p>
            <p><strong>Era:</strong> {{ work.era }}</p>
            <p class="canonical">{{ work.canonical_string }}</p>
          </div>
          <div class="card-footer">
            <button @click="playWork(work)">Play</button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="hasSearched && results.length === 0" class="no-results">
      <p>No results found. Try a different search.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { MusicAPI, Work } from '../api/music';

const searchQuery = ref('');
const results = ref<Work[]>([]);
const isLoading = ref(false);
const error = ref('');
const hasSearched = ref(false);

async function handleSearch() {
  if (!searchQuery.value.trim()) return;

  isLoading.value = true;
  error.value = '';
  hasSearched.value = true;

  try {
    results.value = await MusicAPI.search(searchQuery.value);
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Search failed';
    results.value = [];
  } finally {
    isLoading.value = false;
  }
}

function playWork(work: Work) {
  console.log('Play:', work);
  // Navigate to player with selected work
}
</script>

<style scoped>
.search-container {
  max-width: 1000px;
  margin: 0 auto;
}

.search-box {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
}

.search-box input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
}

.search-box input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 5px rgba(102, 126, 234, 0.1);
}

.search-box button {
  padding: 12px 30px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.search-box button:hover:not(:disabled) {
  opacity: 0.9;
}

.search-box button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  background: #ffebee;
  color: #c62828;
  padding: 15px;
  border-radius: 5px;
  margin-bottom: 20px;
}

.results h2 {
  color: #333;
  margin-bottom: 20px;
  font-size: 18px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.result-card {
  background: white;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s;
}

.result-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.card-header {
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.card-header h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.composer {
  margin: 0;
  font-size: 12px;
  opacity: 0.9;
}

.card-body {
  padding: 16px;
  font-size: 13px;
}

.card-body p {
  margin: 8px 0;
  color: #555;
}

.canonical {
  margin-top: 12px !important;
  padding-top: 12px;
  border-top: 1px solid #eee;
  color: #999 !important;
  font-size: 11px !important;
  font-style: italic;
}

.card-footer {
  padding: 12px 16px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
}

.card-footer button {
  flex: 1;
  padding: 10px;
  background: #f0f0f0;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}

.card-footer button:hover {
  background: #667eea;
  color: white;
}

.no-results {
  text-align: center;
  padding: 40px 20px;
  color: #999;
  font-size: 16px;
}
</style>
