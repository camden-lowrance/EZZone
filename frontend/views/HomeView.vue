<template>
  <div class="max-w-[1200px] mx-auto">
    <div class="flex flex-col items-center py-12 pb-8 gap-4">
      <div class="inline-flex">
        <EZZoneLogoHero />
      </div>
      <p class="text-text-secondary text-[1.1rem] tracking-[0.04em] uppercase">
        Agricultural Management Zone Generator
      </p>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <!-- Upload Section -->
      <div class="card">
        <h2>Upload Data</h2>
        <p class="text-muted mb-6">
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
            multiple
            class="hidden"
            @change="handleFileSelect"
          />
          <div class="text-5xl mb-2">📁</div>
          <p v-if="!selectedFiles.length">Drop files here or click to browse</p>
          <p v-else-if="selectedFiles.length === 1" class="text-success">{{ selectedFiles[0].name }}</p>
          <p v-else class="text-success">{{ selectedFiles.length }} files selected</p>
          <p class="text-base text-muted">Supports all GDAL vector formats · Single or multiple ZIPs · Multiple files with matching schema</p>
        </div>
      </div>

      <!-- Configuration Section -->
      <div class="card">
        <h2>Ready to Process?</h2>
        <p class="text-muted mb-6">
          We will automatically detect the coordinate system and extract data points
          from your file to create management zones.
        </p>

        <div class="alert alert-info">
          <strong>Auto-Processing:</strong>
          <ul class="mt-2 text-base" style="padding-left: 1rem">
            <li>Automatic CRS Detection</li>
            <li>Universal Geometry Support</li>
            <li>Intelligent Data Extraction</li>
          </ul>
        </div>

        <div class="flex gap-4 mt-6">
          <button
            class="btn btn-secondary btn-large"
            @click="useSampleData"
          >
            Use Sample Data
          </button>
          <button
            class="btn btn-primary btn-large"
            :disabled="!canProcess"
            @click="processFile"
          >
            Process File
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useZoneStore } from '../stores/zoneStore'
import { STEPS } from '../steps.js'
import EZZoneLogoHero from '../components/EZZoneLogoHero.vue'

const store = useZoneStore()

const isDragging = ref(false)
const fileInput = ref(null)
// Keep File objects outside Vue reactivity to prevent Proxy wrapping breaking FormData
let rawFiles = []
const selectedFiles = ref([]) // UI-only: stores {name, size} metadata
const isSampleMode = ref(false)

const canProcess = computed(() => selectedFiles.value.length > 0)

function setFiles(fileList) {
  rawFiles = Array.from(fileList)
  selectedFiles.value = rawFiles.map(f => ({ name: f.name, size: f.size }))
}

function handleDrop(e) {
  isDragging.value = false
  if (e.dataTransfer.files.length) setFiles(e.dataTransfer.files)
}

function handleFileSelect(e) {
  if (e.target.files.length) setFiles(e.target.files)
}

async function useSampleData() {
  rawFiles = []
  selectedFiles.value = []
  isSampleMode.value = true
  await store.initSession([], '', '', true)
  if (!store.error) {
    store.uploadMeta = {
      fileLabel: 'Sample Data',
      rawFiles: [],
      initialZ: store.results.detectedZ,
      initialCrs: store.results.detectedCrs,
      isSampleMode: true,
    }
    store.step = STEPS.DATA
  }
}

async function processFile() {
  if (rawFiles.length) {
    isSampleMode.value = false
    await store.initSession(rawFiles)
    if (!store.error) {
      const label = rawFiles.length === 1 ? rawFiles[0].name : `${rawFiles.length} files`
      store.uploadMeta = {
        fileLabel: label,
        rawFiles: rawFiles,
        initialZ: store.results.detectedZ,
        initialCrs: store.results.detectedCrs,
        isSampleMode: false,
      }
      store.step = STEPS.DATA
    }
  }
}
</script>
