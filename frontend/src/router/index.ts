import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Player',
        component: () => import('../pages/Player.vue'),
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('../pages/Search.vue'),
      },
      {
        path: 'library',
        name: 'Library',
        component: () => import('../pages/Library.vue'),
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('../pages/Admin.vue'),
        meta: { requiresAdmin: true },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin);

  if (requiresAuth && !authStore.token) {
    next('/login');
  } else if (requiresAdmin && authStore.role !== 'admin') {
    next('/');
  } else {
    next();
  }
});

export default router;
