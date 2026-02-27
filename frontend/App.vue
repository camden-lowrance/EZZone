<template>
  <div class="flex flex-col min-h-screen">
    <header v-show="store.step !== STEPS.UPLOAD"
            style="background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); box-shadow: 0 1px 16px rgba(0,255,136,0.15); padding: 1rem 0; position: sticky; top: 0; z-index: 100;">
      <div class="container flex items-center justify-center">
        <div class="flex items-center gap-2">
          <EZZoneLogo />
        </div>
      </div>
    </header>

    <main class="flex-1 py-6">
      <div class="container">
        <HomeView v-if="store.step === STEPS.UPLOAD" />
        <DataView v-else-if="store.step === STEPS.DATA" />
        <DrawBoundaryView v-else-if="store.step === STEPS.BOUNDARY" />
        <ZonesView v-else-if="store.step === STEPS.ZONES" />
        <FinalizeView v-else-if="store.step === STEPS.FINALIZE" />
      </div>
    </main>

    <footer style="background: var(--bg-secondary); border-top: 1px solid var(--border-color); padding: 1.5rem 0; margin-top: auto;">
      <div class="container text-center text-base" style="color: var(--text-secondary);">
        <p>EZZone - Agricultural Management Zone Generator</p>
        <p>University of Georgia Precision Agriculture</p>
      </div>
    </footer>

    <div v-if="store.loading" class="loading-overlay">
      <div class="text-center">
        <div class="spinner w-12 h-12 border-4 mx-auto mb-4"></div>
        <p class="text-text-secondary">Processing...</p>
      </div>
    </div>

    <div v-if="store.error" class="fixed top-6 left-1/2 -translate-x-1/2 z-[1001] max-w-[500px] w-[90%]">
      <div class="alert alert-error">
        {{ store.error }}
        <button @click="store.error = null" class="btn-close">&times;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useZoneStore } from './stores/zoneStore'
import { STEPS } from './steps.js'
import EZZoneLogo from './components/EZZoneLogo.vue'
import HomeView from './views/HomeView.vue'
import DataView from './views/DataView.vue'
import DrawBoundaryView from './views/DrawBoundaryView.vue'
import ZonesView from './views/ZonesView.vue'
import FinalizeView from './views/FinalizeView.vue'

const store = useZoneStore()
</script>

<style scoped>
.logo svg {
  height: 3rem;
  width: auto;
}

.btn-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 1.25rem;
  cursor: pointer;
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
}
</style>
