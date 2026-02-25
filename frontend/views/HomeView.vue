<template>
  <div class="home-view">
    <div class="grid grid-2">
      <!-- Upload Section -->
      <div class="card">
        <h2>Upload Data</h2>
        <p class="text-muted mb-lg">
          Upload any vector file (CSV, GeoJSON, Shapefile, KML, etc.) 
          containing point data or geometries with values.
        </p>
        
        <div 
          class="file-drop"
          :class="{ dragover: isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="handleDrop"
          @click="$refs.fileInput.click()"
        >
          <input 
            ref="fileInput"
            type="file"
            style="display: none"
            @change="handleFileSelect"
          />
          <div class="file-drop-icon">📁</div>
          <p v-if="!selectedFile">Drop your file here or click to browse</p>
          <p v-else class="text-success">{{ selectedFile.name }}</p>
          <p class="text-small text-muted">Supports all GDAL vector formats</p>
        </div>

        <div v-if="selectedFile" class="mt-md">
          <div class="form-group">
            <label class="form-label">Z Column (Optional)</label>
            <input 
              v-model="store.config.zColumn" 
              type="text" 
              class="form-input"
              placeholder="e.g. Yield, NDVI, EC"
            />
            <p class="text-small text-muted mt-sm">
              The numeric column to use for zone generation. 
              We'll try to auto-detect it if left blank.
            </p>
          </div>
        </div>
      </div>
      
      <!-- Configuration Section -->
      <div class="card">
        <h2>Ready to Process?</h2>
        <p class="text-muted mb-lg">
          We will automatically detect the coordinate system and extract data points 
          from your file to create management zones.
        </p>

        <div class="alert alert-info">
          <strong>Auto-Processing:</strong>
          <ul class="mt-sm text-small" style="padding-left: 1rem">
            <li>Automatic CRS Detection</li>
            <li>Universal Geometry Support</li>
            <li>Intelligent Data Extraction</li>
          </ul>
        </div>
        
        <div class="flex gap-md mt-lg">
          <button 
            class="btn btn-secondary btn-large"
            @click="useSampleData"
          >
            Use Sample Data
          </button>
          <button 
            class="btn btn-primary btn-large"
            :disabled="!canContinue"
            @click="continueToBoundary"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useZoneStore } from '../stores/zoneStore'

const store = useZoneStore()

const isDragging = ref(false)
const fileInput = ref(null)
const selectedFile = ref(null)

const canContinue = computed(() => !!selectedFile.value)

function handleDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length) {
    selectedFile.value = files[0]
  }
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length) {
    selectedFile.value = files[0]
  }
}

async function useSampleData() {
  await store.initSession(null)
}

async function continueToBoundary() {
  if (selectedFile.value) {
    await store.initSession(selectedFile.value, store.config.zColumn)
  }
}
</script>

<style scoped>
.home-view {
  max-width: 1200px;
  margin: 0 auto;
}

.file-drop-icon {
  font-size: 3rem;
  margin-bottom: var(--space-sm);
}

.file-drop p {
  margin: var(--space-xs) 0;
}

.text-success {
  color: var(--accent-green);
  font-weight: 600;
}
</style>
