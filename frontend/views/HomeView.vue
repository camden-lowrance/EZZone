<template>
  <div class="home-view">
    <div v-if="!sessionReady" class="hero">
      <div class="hero-logo-wrap">
        <img src="/img/ezzone_logo_large.png" alt="EZZone" class="hero-logo" />
      </div>
      <p class="hero-tagline">Agricultural Management Zone Generator</p>
    </div>

    <div v-if="!sessionReady" class="grid grid-2">
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
            multiple
            style="display: none"
            @change="handleFileSelect"
          />
          <div class="file-drop-icon">📁</div>
          <p v-if="!selectedFiles.length">Drop files here or click to browse</p>
          <p v-else-if="selectedFiles.length === 1" class="text-success">{{ selectedFiles[0].name }}</p>
          <p v-else class="text-success">{{ selectedFiles.length }} files selected</p>
          <p class="text-small text-muted">Supports all GDAL vector formats · Single or multiple ZIPs · Multiple files with matching schema</p>
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
            Use Sample Data (Blount Harvest)
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

    <!-- Data Summary (shown after processing) -->
    <div v-else class="card summary-card">
      <h2>Data Summary</h2>
      <p class="text-muted mb-lg">
        We detected the following from your file. Verify the value column before drawing the boundary.
      </p>

      <div class="summary-grid">
        <div class="summary-item">
          <span class="summary-label">File</span>
          <span class="summary-value">{{ selectedFiles.length === 0 ? 'Sample Data' : selectedFiles.length === 1 ? selectedFiles[0].name : `${selectedFiles.length} files` }}</span>
        </div>
        <div class="summary-item">
          <label class="summary-label" :for="store.results.isCrsGuessed ? 'crs-input' : undefined">
            {{ store.results.isCrsGuessed ? 'CRS (Guessed)' : 'Detected CRS' }}
          </label>
          <input
            v-if="store.results.isCrsGuessed"
            id="crs-input"
            v-model="editableCrs"
            type="text"
            class="form-input"
            placeholder="e.g. epsg:4326"
          />
          <span v-else class="summary-value">{{ store.results.detectedCrs || 'Auto' }}</span>
        </div>
        <div class="summary-item summary-item-wide">
          <label class="summary-label" for="z-column-select">Value Column</label>
          <div class="z-column-control">
            <select
              v-if="store.results.allColumns.length"
              id="z-column-select"
              v-model="store.results.detectedZ"
              class="form-input"
            >
              <option disabled value="">Select a column...</option>
              <optgroup label="Numeric Columns">
                <option v-for="col in store.results.numericColumns" :key="col" :value="col">
                  {{ col }}
                </option>
              </optgroup>
              <optgroup v-if="otherColumns.length" label="Other Columns">
                <option v-for="col in otherColumns" :key="col" :value="col">
                  {{ col }}
                </option>
              </optgroup>
            </select>
            <input
              v-else
              id="z-column-select"
              v-model="store.results.detectedZ"
              type="text"
              class="form-input"
              placeholder="e.g. Yield, NDVI, EC"
            />
          </div>
        </div>
      </div>

      <!-- Data Preview Table -->
      <div v-if="store.results.previewData.length" class="mt-lg">
        <label class="summary-label">Data Preview</label>
        <div class="preview-table-container">
          <table class="preview-table">
            <thead>
              <tr>
                <th v-for="col in store.results.allColumns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in store.results.previewData" :key="idx">
                <td v-for="col in store.results.allColumns" :key="col">
                  {{ formatValue(row[col]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="flex justify-between mt-lg">
        <button class="btn btn-secondary btn-large" @click="startOver">
          ← Start Over
        </button>
        <button class="btn btn-primary btn-large" @click="continueToBoundary">
          Draw Boundary →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useZoneStore } from '../stores/zoneStore'
import { STEPS } from '../steps.js'

const store = useZoneStore()

const isDragging = ref(false)
const fileInput = ref(null)
// Keep File objects outside Vue reactivity to prevent Proxy wrapping breaking FormData
let rawFiles = []
const selectedFiles = ref([]) // UI-only: stores {name, size} metadata
const sessionReady = ref(false)
const isSampleMode = ref(false)
const editableCrs = ref('')
let lastProcessedZ = null
let lastProcessedCrs = null

const FLAT_FILE_EXTS = new Set(['csv', 'txt', 'tsv', 'xlsx', 'xls'])
const isFlatFile = computed(() => {
  if (selectedFiles.value.length !== 1) return false
  const ext = selectedFiles.value[0].name.split('.').pop().toLowerCase()
  return FLAT_FILE_EXTS.has(ext)
})

const canProcess = computed(() => selectedFiles.value.length > 0)

const otherColumns = computed(() => {
  const numericSet = new Set(store.results.numericColumns)
  return store.results.allColumns.filter(col => !numericSet.has(col))
})

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
  lastProcessedZ = store.results.detectedZ
  editableCrs.value = store.results.detectedCrs
  lastProcessedCrs = store.results.detectedCrs
  sessionReady.value = true
}

async function processFile() {
  if (rawFiles.length) {
    isSampleMode.value = false
    await store.initSession(rawFiles)
    if (!store.error) {
      lastProcessedZ = store.results.detectedZ
      editableCrs.value = store.results.detectedCrs
      lastProcessedCrs = store.results.detectedCrs
      sessionReady.value = true
    }
  }
}

async function continueToBoundary() {
  const zChanged = store.results.detectedZ !== lastProcessedZ
  const crsChanged = editableCrs.value !== lastProcessedCrs

  if (zChanged || crsChanged) {
    await store.initSession(
      rawFiles.length ? rawFiles : [],
      store.results.detectedZ,
      editableCrs.value,
      isSampleMode.value
    )
    if (store.error) return
    lastProcessedZ = store.results.detectedZ
    lastProcessedCrs = editableCrs.value
  }
  store.step = STEPS.BOUNDARY
}

function startOver() {
  sessionReady.value = false
  isSampleMode.value = false
  rawFiles = []
  selectedFiles.value = []
  lastProcessedZ = null
  editableCrs.value = ''
  lastProcessedCrs = null
  store.reset()
}

function formatValue(val) {
  if (typeof val === 'number') {
    return Number.isInteger(val) ? val : val.toFixed(4)
  }
  return val
}
</script>

<style scoped>
.home-view {
  max-width: 1200px;
  margin: 0 auto;
}

.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-2xl) 0 var(--space-xl);
  gap: var(--space-md);
}

.hero-logo-wrap {
  background: #1c1e20;
  border-radius: 1rem;
  display: inline-flex;
}

.hero-logo {
  width: min(26rem, 80vw);
  filter: drop-shadow(0 0 1.5rem rgba(0, 255, 136, 0.4));
  display: block;
}

.hero-tagline {
  font-size: 1.1rem;
  color: var(--text-secondary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
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

.summary-card {
  max-width: 900px;
  margin: 0 auto;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-lg);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: var(--space-lg);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.summary-item-wide {
  grid-column: 1 / -1;
}

.summary-label {
  font-size: 0.875rem;
  color: var(--accent-cyan);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.z-column-control {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.detected-hint {
  font-size: 0.875rem;
  color: var(--accent-green);
}

.preview-table-container {
  overflow-x: auto;
  margin-top: var(--space-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 1rem;
}

.preview-table th,
.preview-table td {
  padding: var(--space-sm);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.preview-table th {
  background: var(--bg-elevated);
  color: var(--accent-cyan);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.preview-table tr:last-child td {
  border-bottom: none;
}
</style>
