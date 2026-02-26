<template>
  <div class="app">
    <header class="app-header" v-show="store.step !== STEPS.UPLOAD">
      <div class="container flex items-center justify-center">
        <div class="logo">
          <img src="/img/ezzone_logo_header.png" alt="EZZone" />
        </div>
      </div>
    </header>

    <main class="app-main">
      <div class="container">
        <HomeView v-if="store.step === STEPS.UPLOAD" />
        <DrawBoundaryView v-else-if="store.step === STEPS.BOUNDARY" />
        <ZonesView v-else-if="store.step === STEPS.ZONES" />
        <FinalizeView v-else-if="store.step === STEPS.FINALIZE" />
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
      <div class="alert alert-error" style="white-space: pre-line; position: relative; padding-right: 2.5rem">
        {{ store.error }}
        <button @click="store.error = null" class="btn-close" style="position: absolute; top: 0.5rem; right: 0.5rem">&times;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useZoneStore } from './stores/zoneStore'
import { STEPS } from './steps.js'
import HomeView from './views/HomeView.vue'
import DrawBoundaryView from './views/DrawBoundaryView.vue'
import ZonesView from './views/ZonesView.vue'
import FinalizeView from './views/FinalizeView.vue'

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
  border-bottom: 1px solid var(--accent-neon);
  box-shadow: 0 1px 16px rgba(0, 255, 136, 0.15);
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
  height: 3rem;
  display: block;
}

.logo-text {
  font-size: 1.5rem;
  font-weight: 700;
  background: var(--gradient-logo);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
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
  top: var(--space-lg);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1001;
  max-width: 500px;
  width: 90%;
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
