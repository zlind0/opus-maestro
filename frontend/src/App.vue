<template>
  <div id="app">
    <router-view v-if="!isLoading" />
    <div v-else class="loading">
      <p>Loading...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from './stores/auth';

const isLoading = ref(true);
const authStore = useAuthStore();

onMounted(async () => {
  // Check if user has valid token
  const token = localStorage.getItem('token');
  if (token) {
    authStore.setToken(token);
  }
  isLoading.value = false;
});
</script>

<style scoped>
#app {
  min-height: 100vh;
  background: #f5f5f5;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  font-size: 18px;
  color: #666;
}
</style>
