<template>
  <div class="app">
    <header class="app-header">
      <div class="container flex items-center justify-between">
        <div class="logo">
          <img src="/static/img/logonew.png" alt="EZZone" />
          <span class="logo-text">EZZone</span>
        </div>
        <nav class="nav">
          <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
            Home
          </router-link>
          <router-link to="/draw-boundary" class="nav-link" :class="{ active: $route.path === '/draw-boundary' }">
            Draw Boundary
          </router-link>
          <router-link to="/zones" class="nav-link" :class="{ active: $route.path === '/zones' }">
            Zones
          </router-link>
          <router-link to="/finalize" class="nav-link" :class="{ active: $route.path === '/finalize' }">
            Finalize
          </router-link>
        </nav>
      </div>
    </header>
    
    <main class="app-main">
      <div class="container">
        <ProgressStepper :current-step="store.step" />
        <router-view />
      </div>
    </main>
    
    <footer class="app-footer">
      <div class="container text-center text-muted text-small">
        <p>EZZone - Agricultural Management Zone Generator</p>
        <p>University of Georgia Precision Agriculture</p>
      </div>
    </footer>
    
    <div v-if="store.loading" class="loading-overlay">
      <div class="loading-content">
        <div class="spinner"></div>
        <p>Processing...</p>
      </div>
    </div>
    
    <div v-if="store.error" class="error-toast">
      <div class="alert alert-error">
        {{ store.error }}
        <button @click="store.error = null" class="btn-close">&times;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useZoneStore } from './stores/zoneStore'
import ProgressStepper from './components/ProgressStepper.vue'

const store = useZoneStore()
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: var(--space-md) 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.logo img {
  height: 40px;
}

.logo-text {
  font-size: 1.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #e00203, #0870ae);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav {
  display: flex;
  gap: var(--space-xs);
}

.nav-link {
  padding: var(--space-sm) var(--space-md);
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.nav-link.active {
  color: var(--accent-primary);
  background: rgba(29, 155, 240, 0.1);
}

.app-main {
  flex: 1;
  padding: var(--space-lg) 0;
}

.app-footer {
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  padding: var(--space-lg) 0;
  margin-top: auto;
}

.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 20, 25, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-content {
  text-align: center;
}

.loading-content .spinner {
  width: 48px;
  height: 48px;
  border-width: 4px;
  margin: 0 auto var(--space-md);
}

.loading-content p {
  color: var(--text-secondary);
}

.error-toast {
  position: fixed;
  bottom: var(--space-lg);
  right: var(--space-lg);
  z-index: 1001;
  max-width: 400px;
}

.btn-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 1.25rem;
  cursor: pointer;
  margin-left: var(--space-sm);
}
</style>
