<template>
  <div id="classical-app">
    <router-view />
    <PlayerBar v-if="authStore.isLoggedIn" />
  </div>
</template>

<script setup lang="ts">
import PlayerBar from '@/components/PlayerBar.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>
