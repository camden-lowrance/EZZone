<template>
  <div class="home-view">
    <div class="grid grid-2">
      <!-- Upload Section -->
      <div class="card">
        <h2>Upload Data</h2>
        <p class="text-muted mb-lg">
          Upload a CSV or TXT file with X, Y, Z coordinates. 
          Or use the sample data to try it out.
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
            accept=".csv,.txt"
            style="display: none"
            @change="handleFileSelect"
          />
          <div class="file-drop-icon">📁</div>
          <p>Drop your file here or click to browse</p>
          <p class="text-small text-muted">Supports CSV and TXT files</p>
        </div>
        
        <!-- Column Selection -->
        <div v-if="parsedData" class="mt-lg">
          <h4>Select Columns</h4>
          <p class="text-small text-muted mb-md">
            Map your file columns to X (Longitude), Y (Latitude), and Z (Value)
          </p>
          
          <div class="grid grid-3 gap-sm">
            <div class="form-group">
              <label class="form-label">X (Longitude)</label>
              <select v-model="columns.x" class="form-select">
                <option v-for="col in headers" :key="col" :value="col">{{ col }}</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Y (Latitude)</label>
              <select v-model="columns.y" class="form-select">
                <option v-for="col in headers" :key="col" :value="col">{{ col }}</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Z (Value)</label>
              <select v-model="columns.z" class="form-select">
                <option v-for="col in headers" :key="col" :value="col">{{ col }}</option>
              </select>
            </div>
          </div>
          
          <!-- Preview -->
          <div class="mt-md">
            <h4>Data Preview</h4>
            <div class="table-wrapper">
              <table class="table">
                <thead>
                  <tr>
                    <th v-for="col in headers" :key="col">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in previewRows" :key="i">
                    <td v-for="col in headers" :key="col">{{ row[col] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="text-small text-muted mt-sm">
              {{ parsedData.length }} data points
            </p>
          </div>
        </div>
      </div>
      
      <!-- Configuration Section -->
      <div class="card">
        <h2>Configuration</h2>
        
        <div class="form-group">
          <label class="form-label">Coordinate Reference System (EPSG)</label>
          <input 
            v-model="store.epsg" 
            type="text" 
            class="form-input"
            placeholder="4326"
          />
          <p class="text-small text-muted mt-sm">
            4326 = WGS84 (lat/lon), 326XX = UTM zone XX
          </p>
        </div>
        
        <div class="form-group">
          <label class="form-label">Field Type</label>
          <div class="radio-group">
            <label class="radio-option">
              <input 
                type="radio" 
                v-model="store.fieldType" 
                :value="1"
                @change="updateFieldType"
              />
              <span>Rectangular</span>
            </label>
            <label class="radio-option">
              <input 
                type="radio" 
                v-model="store.fieldType" 
                :value="2"
                @change="updateFieldType"
              />
              <span>Center Pivot with Variable Rate Irrigation (VRI)</span>
            </label>
            <label class="radio-option">
              <input 
                type="radio" 
                v-model="store.fieldType" 
                :value="3"
                @change="updateFieldType"
              />
              <span>All other field types (Irregular)</span>
            </label>
          </div>
        </div>
        
        <!-- Rectangular / Irregular Options -->
        <div v-if="store.fieldType === 1 || store.fieldType === 3" class="form-group">
          <label class="form-label">Zone Spacing ({{ store.units }})</label>
          <input 
            v-model.number="store.rowSpacing" 
            type="number" 
            class="form-input"
            min="1"
          />
        </div>
        
        <!-- VRI Options -->
        <div v-if="store.fieldType === 2">
          <div class="form-group">
            <label class="form-label">Span Spacing ({{ store.units }})</label>
            <input 
              v-model.number="store.pivotSpacing" 
              type="number" 
              class="form-input"
              min="1"
            />
          </div>
          <div class="form-group">
            <label class="form-label">Pivot Length ({{ store.units }})</label>
            <input 
              v-model.number="store.pivotLength" 
              type="number" 
              class="form-input"
              min="1"
            />
          </div>
        </div>
        
        <div class="form-group">
          <label class="form-label">Units</label>
          <select v-model="store.units" class="form-select">
            <option value="m">Meters</option>
            <option value="f">Feet</option>
          </select>
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
import { useRouter } from 'vue-router'
import { useZoneStore } from '../stores/zoneStore'
import Papa from 'papaparse'

const router = useRouter()
const store = useZoneStore()

const isDragging = ref(false)
const fileInput = ref(null)
const parsedData = ref(null)
const headers = ref([])
const columns = ref({ x: '', y: '', z: '' })

const previewRows = computed(() => {
  if (!parsedData.value) return []
  return parsedData.value.slice(0, 5)
})

const canContinue = computed(() => {
  return parsedData.value && columns.value.x && columns.value.y && columns.value.z
})

function handleDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length) {
    parseFile(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length) {
    parseFile(files[0])
  }
}

function parseFile(file) {
  Papa.parse(file, {
    header: true,
    skipEmptyLines: true,
    complete: (results) => {
      if (results.errors.length) {
        store.error = 'Error parsing file: ' + results.errors[0].message
        return
      }
      
      parsedData.value = results.data
      headers.value = Object.keys(results.data[0] || {})
      
      // Auto-detect column names
      const xCandidates = headers.value.filter(h => 
        /^(x|lon|long|easting)/i.test(h)
      )
      const yCandidates = headers.value.filter(h => 
        /^(y|lat|lat|northing)/i.test(h)
      )
      const zCandidates = headers.value.filter(h => 
        /^(z|val|value|ec|yield|ndvi)/i.test(h)
      )
      
      columns.value = {
        x: xCandidates[0] || headers.value[0],
        y: yCandidates[0] || headers.value[1] || headers.value[0],
        z: zCandidates[0] || headers.value[2] || headers.value[0]
      }
    }
  })
}

function updateFieldType() {
  // Reset field-specific defaults
  if (store.fieldType === 1 || store.fieldType === 3) {
    store.rowSpacing = 100
  } else if (store.fieldType === 2) {
    store.pivotSpacing = 50
    store.pivotLength = 500
  }
}

async function useSampleData() {
  parsedData.value = [{ sample: true }]
  headers.value = ['X', 'Y', 'Z']
  columns.value = { x: 'X', y: 'Y', z: 'Z' }
  
  await continueToBoundary()
}

async function continueToBoundary() {
  try {
    // Determine file - use sample if no file uploaded
    const file = parsedData.value[0]?.sample ? null : fileInput.value?.files[0]
    
    await store.initSession(file, columns.value)
    router.push('/draw-boundary')
  } catch (e) {
    // Error handled in store
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

.table-wrapper {
  max-height: 200px;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

@media (max-width: 768px) {
  .grid-3 {
    grid-template-columns: 1fr;
  }
}
</style>
