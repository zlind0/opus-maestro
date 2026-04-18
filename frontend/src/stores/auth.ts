import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../api/client';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'));
  const username = ref<string | null>(localStorage.getItem('username'));
  const role = ref<string | null>(localStorage.getItem('role'));
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function login(input: { username: string; password: string }) {
    isLoading.value = true;
    error.value = null;
    try {
      const formData = new FormData();
      formData.append('username', input.username);
      formData.append('password', input.password);

      const response = await api.post('/api/v1/auth/token', formData);
      const { access_token, token_type } = response.data;

      token.value = access_token;
      username.value = input.username;

      localStorage.setItem('token', access_token);
      localStorage.setItem('username', input.username);
      localStorage.setItem('tokenType', token_type);

      // Fetch user info to get role
      await fetchUserInfo();
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Login failed';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchUserInfo() {
    try {
      const response = await api.get('/api/v1/auth/me');
      role.value = response.data.role;
      localStorage.setItem('role', response.data.role);
    } catch (err) {
      console.error('Failed to fetch user info:', err);
    }
  }

  function logout() {
    token.value = null;
    username.value = null;
    role.value = null;
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
  }

  function setToken(newToken: string) {
    token.value = newToken;
    localStorage.setItem('token', newToken);
  }

  const state = {
    token,
    username,
    role,
    isLoading,
    error,
    login,
    logout,
    setToken,
    fetchUserInfo,
  };

  return state;
});
