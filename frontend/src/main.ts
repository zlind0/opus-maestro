import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');

// Register service worker (only in production)
if (import.meta.env.PROD) {
  if (typeof (window as any).__PWA_REGISTER__ === 'function') {
    const { registerSW } = (window as any).__PWA_REGISTER__;
    registerSW();
  }
}
