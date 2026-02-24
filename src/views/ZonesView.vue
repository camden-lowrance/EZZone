<template>
  <div class="zones-view">
    <div class="grid grid-2">
      <!-- Map & Controls -->
      <div class="card">
        <h2>Generated Zones</h2>
        <p class="text-muted mb-md">
          View the generated zones. Adjust the number of classes to find 
          the optimal grouping.
        </p>
        
        <div ref="mapContainer" class="map-container mb-md"></div>
        
        <!-- Class Selection -->
        <div class="form-group">
          <label class="form-label">
            Number of Classes: {{ numClasses }}
          </label>
          <input 
            v-model.number="numClasses"
            type="range"
            class="slider"
            min="2"
            max="15"
            @change="regenerateZones"
          />
          <div class="range-labels">
            <span>2</span>
            <span>15</span>
          </div>
        </div>
        
        <!-- Legend -->
        <div v-if="store.legend" class="legend">
          <h4 class="mb-sm">Legend</h4>
          <div class="legend-items">
            <div 
              v-for="(item, i) in store.legend" 
              :key="i"
              class="legend-item"
            >
              <span 
                class="legend-color" 
                :style="{ background: item.color }"
              ></span>
              <span class="legend-label">{{ item.label }}</span>
            </div>
          </div>
        </div>
        
        <div class="flex justify-between mt-lg">
          <button class="btn btn-secondary" @click="goBack">
            ← Back
          </button>
          <button class="btn btn-success" @click="continueToFinalize">
            Finalize Zones →
          </button>
        </div>
      </div>
      
      <!-- GVF Chart -->
      <div class="card">
        <h2>Goodness of Variance Fit (GVF)</h2>
        <p class="text-muted mb-md">
          The GVF chart shows how well the zones group your data. 
          Higher values indicate better grouping.
        </p>
        
        <div class="chart-container">
          <Line :data="chartData" :options="chartOptions" />
        </div>
        
        <div class="mt-lg">
          <h4>Class Breaks</h4>
          <table class="table">
            <thead>
              <tr>
                <th>Class</th>
                <th>Range</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, i) in classBreakTable" :key="i">
                <td>{{ i + 1 }}</td>
                <td>{{ item }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="alert alert-info mt-lg">
          <strong>Tip:</strong> The optimal number of classes is typically where 
          the GVF curve starts to flatten out (the "elbow").
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useZoneStore } from '../stores/zoneStore'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import Map from 'ol/Map'
import View from 'ol/View'
import VectorSource from 'ol/source/Vector.js'
import VectorLayer from 'ol/layer/Vector.js'
import { GeoJSON } from 'ol/format'
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const router = useRouter()
const store = useZoneStore()

const mapContainer = ref(null)
const numClasses = ref(10)
let map = null
let zonesLayer = null
let zonesSource = null

const chartData = computed(() => ({
  labels: store.gvf.map((_, i) => i + 2),
  datasets: [{
    label: 'GVF',
    data: store.gvf.map(g => g[1]),
    borderColor: '#1d9bf0',
    backgroundColor: 'rgba(29, 155, 240, 0.1)',
    fill: true,
    tension: 0.3
  }]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    }
  },
  scales: {
    x: {
      title: {
        display: true,
        text: 'Number of Classes'
      },
      grid: {
        color: 'rgba(56, 68, 77, 0.5)'
      },
      ticks: {
        color: '#8b98a5'
      }
    },
    y: {
      title: {
        display: true,
        text: 'GVF'
      },
      grid: {
        color: 'rgba(56, 68, 77, 0.5)'
      },
      ticks: {
        color: '#8b98a5'
      },
      min: 0,
      max: 1
    }
  }
}

const classBreakTable = computed(() => {
  if (!store.classBreaks.length) return []
  return store.classBreaks.map((cb, i) => {
    const start = cb.toFixed(2)
    const end = store.classBreaks[i + 1]?.toFixed(2) || '+'
    return `${start} - ${end}`
  })
})

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map) {
    map.setTarget(null)
  }
})

function initMap() {
  zonesSource = new VectorSource()
  
  zonesLayer = new VectorLayer({
    source: zonesSource,
    style: (feature) => {
      const classNum = feature.get('class')
      const colors = [
        '#00ba7c', '#1d9bf0', '#f4212e', '#ff7a00', '#ffd400',
        '#9b5de5', '#00f5d4', '#fee440', '#f15bb5', '#00bbf9',
        '#9b5de5', '#f15bb5', '#00f5d4', '#fee440'
      ]
      return {
        fillColor: colors[classNum - 1] || colors[0],
        fillOpacity: 0.5,
        strokeColor: colors[classNum - 1] || colors[0],
        strokeWidth: 1
      }
    }
  })
  
  map = new Map({
    target: mapContainer.value,
    layers: [
      new TileLayer({
        source: new OSM()
      }),
      zonesLayer
    ],
    view: new View({
      center: [0, 0],
      zoom: 2
    })
  })
  
  loadZones()
}

function loadZones() {
  if (!store.zones || !zonesSource) return
  
  zonesSource.clear()
  const geojson = store.zones
  const features = new GeoJSON().readFeatures(geojson)
  zonesSource.addFeatures(features)
  
  // Fit view
  const extent = zonesSource.getExtent()
  map.getView().fit(extent, { padding: [50, 50, 50, 50] })
}

async function regenerateZones() {
  try {
    await store.generateZones(numClasses.value)
    // Need to fetch zones again after generation
    // Note: API might need updating to return zones
  } catch (e) {
    // Error handled in store
  }
}

function goBack() {
  router.push('/draw-boundary')
}

async function continueToFinalize() {
  try {
    await store.finalizeZones(numClasses.value)
    router.push('/finalize')
  } catch (e) {
    // Error handled in store
  }
}
</script>

<style scoped>
.zones-view {
  max-width: 1400px;
  margin: 0 auto;
}

.chart-container {
  height: 300px;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 3px;
}

.legend-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}
</style>
