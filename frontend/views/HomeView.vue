<template>
  <div class="home-view">
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
          <span class="summary-value">{{ selectedFile ? selectedFile.name : 'Sample Data' }}</span>
        </div>
        <div class="summary-item">
          <label class="summary-label" :for="isFlatFile ? 'crs-input' : undefined">
            {{ isFlatFile ? 'CRS' : 'Detected CRS' }}
          </label>
          <input
            v-if="isFlatFile"
            id="crs-input"
            v-model="editableCrs"
            type="text"
            class="form-input"
            placeholder="e.g. epsg:4326, epsg:32614"
          />
          <span v-else class="summary-value">{{ store.results.detectedCrs || 'Auto' }}</span>
        </div>
        <div class="summary-item summary-item-wide">
          <label class="summary-label" for="z-column-select">Value Column</label>
          <div class="z-column-control">
            <select
              v-if="store.results.allColumns.length"
              id="z-column-select"
              v-model="editableZ"
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
              v-model="editableZ"
              type="text"
              class="form-input"
              placeholder="e.g. Yield, NDVI, EC"
            />
            <span class="detected-hint" v-if="store.results.detectedZ && !editableZ">
              Detected: <strong>{{ store.results.detectedZ }}</strong>
            </span>
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

const store = useZoneStore()

const isDragging = ref(false)
const fileInput = ref(null)
const selectedFile = ref(null)
const sessionReady = ref(false)
const editableZ = ref('')
const editableCrs = ref('')

const FLAT_FILE_EXTS = new Set(['csv', 'txt', 'tsv', 'xlsx', 'xls'])
const isFlatFile = computed(() => {
  if (!selectedFile.value) return false
  const ext = selectedFile.value.name.split('.').pop().toLowerCase()
  return FLAT_FILE_EXTS.has(ext)
})

const canProcess = computed(() => !!selectedFile.value)

const otherColumns = computed(() => {
  const numericSet = new Set(store.results.numericColumns)
  return store.results.allColumns.filter(col => !numericSet.has(col))
})

function handleDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length) selectedFile.value = files[0]
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length) selectedFile.value = files[0]
}

async function useSampleData() {
  await store.initSession(null)
  editableZ.value = store.results.detectedZ || ''
  editableCrs.value = store.results.detectedCrs || ''
  sessionReady.value = true
}

async function processFile() {
  if (selectedFile.value) {
    await store.initSession(selectedFile.value, store.config.zColumn)
    if (!store.error) {
      editableZ.value = store.results.detectedZ || ''
      editableCrs.value = store.results.detectedCrs || ''
      sessionReady.value = true
    }
  }
}

async function continueToBoundary() {
  const zChanged = editableZ.value && editableZ.value !== store.results.detectedZ
  const crsChanged = isFlatFile.value && editableCrs.value && editableCrs.value !== store.results.detectedCrs

  if (zChanged || crsChanged) {
    store.config.zColumn = editableZ.value
    await store.initSession(
      selectedFile.value || null,
      editableZ.value,
      isFlatFile.value ? editableCrs.value : ''
    )
    if (store.error) return
  }
  store.step = 2
}

function startOver() {
  sessionReady.value = false
  selectedFile.value = null
  store.config.zColumn = ''
  editableZ.value = ''
  editableCrs.value = ''
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
  font-size: 0.75rem;
  color: var(--text-muted);
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
  font-size: 0.8rem;
  color: var(--text-muted);
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
  font-size: 0.85rem;
}

.preview-table th,
.preview-table td {
  padding: var(--space-sm);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.preview-table th {
  background: var(--bg-secondary);
  color: var(--text-muted);
  font-weight: 600;
}

.preview-table tr:last-child td {
  border-bottom: none;
}
</style>
