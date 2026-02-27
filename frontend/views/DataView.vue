<template>
  <div class="max-w-[1200px] mx-auto">
    <div class="card max-w-[900px] mx-auto">
      <h2>Data Summary</h2>
      <p class="text-muted mb-6">
        We detected the following from your file. Verify the value column before drawing the boundary.
      </p>

      <div class="grid grid-cols-2 gap-6 bg-bg-tertiary rounded p-6">
        <div class="flex flex-col gap-1">
          <span class="summary-label">File</span>
          <span class="summary-value">{{ store.uploadMeta.fileLabel }}</span>
        </div>
        <div class="flex flex-col gap-1">
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
        <div class="flex flex-col gap-1 col-span-2">
          <label class="summary-label" for="z-column-select">Value Column</label>
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

      <!-- Data Preview Table -->
      <div v-if="store.results.previewData.length" class="mt-6">
        <label class="summary-label">Data Preview</label>
        <div class="overflow-x-auto mt-2 border border-[var(--border-color)] rounded">
          <table class="w-full border-collapse text-base">
            <thead>
              <tr>
                <th v-for="col in store.results.allColumns" :key="col"
                    class="px-2 py-2 text-left border-b border-[var(--border-color)] bg-bg-elevated text-accent-cyan font-semibold tracking-[0.04em] whitespace-nowrap">
                  {{ col }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in store.results.previewData" :key="idx">
                <td v-for="col in store.results.allColumns" :key="col"
                    class="px-2 py-2 text-left border-b border-[var(--border-color)] whitespace-nowrap last:border-b-0">
                  {{ formatValue(row[col]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="flex justify-between mt-6">
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
const meta = store.uploadMeta

const editableCrs = ref(meta.initialCrs)

const otherColumns = computed(() => {
  const numericSet = new Set(store.results.numericColumns)
  return store.results.allColumns.filter(col => !numericSet.has(col))
})

async function continueToBoundary() {
  const zChanged = store.results.detectedZ !== meta.initialZ
  const crsChanged = editableCrs.value !== meta.initialCrs

  if (zChanged || crsChanged) {
    await store.initSession(
      meta.rawFiles.length ? meta.rawFiles : [],
      store.results.detectedZ,
      editableCrs.value,
      meta.isSampleMode
    )
    if (store.error) return
  }
  store.step = STEPS.BOUNDARY
}

function startOver() {
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
</style>
