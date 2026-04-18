<template>
  <div class="main-layout">
    <header class="navbar">
      <div class="navbar-content">
        <h1 class="logo">♪ Classical Music</h1>
        <nav class="nav-links">
          <router-link to="/">Player</router-link>
          <router-link to="/search">Search</router-link>
          <router-link to="/library">Library</router-link>
          <router-link v-if="authStore.role === 'admin'" to="/admin">Admin</router-link>
        </nav>
        <button @click="logout" class="logout-btn">Logout</button>
      </div>
    </header>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

function logout() {
  authStore.logout();
  router.push('/login');
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.navbar-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.logo {
  font-size: 24px;
  font-weight: bold;
  margin: 0;
}

.nav-links {
  display: flex;
  gap: 20px;
  flex: 1;
  margin-left: 40px;
}

.nav-links a {
  color: white;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background 0.2s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  background: rgba(255, 255, 255, 0.2);
}

.logout-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.content {
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  padding: 20px;
}

@media (max-width: 768px) {
  .navbar-content {
    flex-wrap: wrap;
    gap: 10px;
  }

  .nav-links {
    margin-left: 0;
    gap: 10px;
    flex-basis: 100%;
    order: 3;
  }

  .nav-links a {
    font-size: 12px;
    padding: 6px 10px;
  }

  .logout-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
}
</style>
