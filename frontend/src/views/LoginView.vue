<template>
  <div class="login-page">
    <div class="login-container skeuo-panel">
      <h1 class="login-title">♫ 古典音乐</h1>
      <p class="login-subtitle">AI驱动的古典音乐智能播放器</p>

      <form @submit.prevent="handleSubmit" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            class="skeuo-input"
            placeholder="输入用户名"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label>密码</label>
          <input
            v-model="password"
            type="password"
            class="skeuo-input"
            placeholder="输入密码"
            required
            autocomplete="current-password"
          />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" class="btn-gold login-btn" :disabled="loading">
          {{ loading ? '请稍候...' : (isRegister ? '注册' : '登录') }}
        </button>

        <p class="toggle-mode" @click="isRegister = !isRegister">
          {{ isRegister ? '已有账号？登录' : '没有账号？注册' }}
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const isRegister = ref(false)
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    if (isRegister.value) {
      await authStore.register(username.value, password.value)
      // After register, auto login
    }
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.login-container {
  width: 100%;
  max-width: 380px;
  text-align: center;
}

.login-title {
  margin-bottom: 0.25rem;
}

.login-subtitle {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin-bottom: 1.5rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  text-align: left;
}

.form-group label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 0.35rem;
}

.error-msg {
  color: #e57373;
  font-size: 0.85rem;
  text-align: center;
}

.login-btn {
  width: 100%;
  justify-content: center;
  margin-top: 0.5rem;
}

.toggle-mode {
  color: var(--accent-gold);
  font-size: 0.82rem;
  cursor: pointer;
  text-align: center;
}
.toggle-mode:hover {
  text-decoration: underline;
}
</style>
