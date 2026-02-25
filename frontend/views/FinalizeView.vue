<template>
  <div class="finalize-view">
    <div class="grid grid-2">
      <!-- Map & Export -->
      <div class="card">
        <h2>Final Zones</h2>
        <p class="text-muted mb-md">
          Your zones are ready. Export them for use in your precision 
          agriculture systems.
        </p>
        
        <div ref="mapContainer" class="map-container mb-md"></div>
        
        <!-- Export Options -->
        <div class="export-section mt-lg">
          <h4 class="mb-md">Export Zones</h4>
          <div class="flex gap-md">
            <button 
              class="btn btn-secondary btn-large"
              @click="exportGeoJSON"
            >
              📄 Download GeoJSON
            </button>
            <button 
              class="btn btn-secondary btn-large"
              @click="exportShapefile"
            >
              📦 Download Shapefile
            </button>
          </div>
        </div>
        
        <div class="flex justify-between mt-lg">
          <button class="btn btn-secondary" @click="goBack">
            ← Back to Zones
          </button>
          <button class="btn btn-primary" @click="startOver">
            Start Over
          </button>
        </div>
      </div>
      
      <!-- Summary -->
      <div class="card">
        <h2>Summary</h2>
        
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-label">Source CRS</span>
            <span class="stat-value" style="font-size: 1rem">{{ store.results.detectedCrs }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Source Column</span>
            <span class="stat-value">{{ store.results.detectedZ }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Classes</span>
            <span class="stat-value">{{ numClasses }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">GVF Score</span>
            <span class="stat-value">{{ gvfScore }}</span>
          </div>
        </div>
        
        <!-- Class Distribution -->
        <div class="mt-lg">
          <h4>Class Distribution</h4>
          <div class="distribution-chart">
            <div 
              v-for="(count, i) in classDistribution" 
              :key="i"
              class="distribution-bar"
            >
              <div 
                class="bar-fill"
                :style="{ 
                  height: `${(count / maxClassCount) * 100}%`,
                  background: (store.results.legend && store.results.legend[i]) ? store.results.legend[i][0] : '#1d9bf0'
                }"
              ></div>
              <span class="bar-label">{{ i + 1 }}</span>
              <span class="bar-count">{{ count }}</span>
            </div>
          </div>
        </div>
        
        <!-- Legend -->
        <div v-if="store.results.legend" class="mt-lg">
          <h4>Legend</h4>
          <div class="legend-items">
            <div 
              v-for="(item, i) in store.results.legend" 
              :key="i"
              class="legend-item"
            >
              <span 
                class="legend-color" 
                :style="{ background: item[0] }"
              ></span>
              <span class="legend-label">{{ item[1] }}</span>
            </div>
          </div>
        </div>
        
        <div class="alert alert-success mt-lg">
          <strong>Done!</strong> Your zones are ready for use in variable-rate 
          application maps or further analysis.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, toRef } from 'vue'
import { useZoneStore } from '../stores/zoneStore'
import Map from 'ol/Map'
import View from 'ol/View'
import VectorSource from 'ol/source/Vector.js'
import VectorLayer from 'ol/layer/Vector.js'
import { GeoJSON } from 'ol/format'
import { Fill, Stroke, Style } from 'ol/style'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'

const store = useZoneStore()

const mapContainer = ref(null)
let map = null
let zonesLayer = null
let zonesSource = null

const numClasses = computed(() => {
  return store.results.legend?.length || 0
})

const gvfScore = computed(() => {
  if (!store.results.gvf?.length) return 'N/A'
  const lastGvf = store.results.gvf[store.results.gvf.length - 1]
  return lastGvf ? lastGvf[1].toFixed(3) : 'N/A'
})

const classDistribution = computed(() => {
  if (!store.results.zones?.features) return []
  
  const counts = {}
  store.results.zones.features.forEach(f => {
    const cls = f.properties?.zone || 1
    counts[cls] = (counts[cls] || 0) + 1
  })
  
  const max = Math.max(...Object.values(counts), 1)
  const result = []
  for (let i = 1; i <= numClasses.value; i++) {
    result.push(counts[i] || 0)
  }
  return result
})

const maxClassCount = computed(() => {
  return Math.max(...classDistribution.value, 1)
})

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map) {
    map.setTarget(null)
  }
})

watch(toRef(store.results, 'zones'), () => {
  if (map) loadZones()
})

function initMap() {
  zonesSource = new VectorSource()
  
  zonesLayer = new VectorLayer({
    source: zonesSource,
    style: (feature) => {
      const classNum = feature.get('zone')
      const color = (store.results.legend && store.results.legend[classNum - 1]) 
        ? store.results.legend[classNum - 1][0] 
        : '#1d9bf0'
      return new Style({
        fill: new Fill({ color: color + '80' }),
        stroke: new Stroke({ color, width: 1 })
      })
    }
  })
  
  map = new Map({
    target: mapContainer.value,
    layers: [
      new TileLayer({
        source: new XYZ({
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          attributions: 'Tiles © Esri'
        })
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
  if (!store.results.zones || !zonesSource) return
  
  zonesSource.clear()
  const features = new GeoJSON().readFeatures(store.results.zones, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857'
  })
  zonesSource.addFeatures(features)
  
  const extent = zonesSource.getExtent()
  map.getView().fit(extent, { padding: [50, 50, 50, 50] })
}

async function exportGeoJSON() {
  await store.exportZones('geojson')
}

async function exportShapefile() {
  await store.exportZones('shapefile')
}

function goBack() {
  store.step = 3
}

function startOver() {
  store.reset()
  store.step = 1
}
</script>

<style scoped>
.finalize-view {
  max-width: 1400px;
  margin: 0 auto;
}

.export-section {
  padding: var(--space-md);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-md);
}

.stat-item {
  padding: var(--space-md);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: var(--space-xs);
}

.distribution-chart {
  display: flex;
  align-items: flex-end;
  gap: var(--space-xs);
  height: 150px;
  padding: var(--space-md);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.distribution-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  position: relative;
}

.bar-fill {
  width: 100%;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  margin-top: auto;
  transition: height var(--transition-normal);
}

.bar-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: var(--space-xs);
}

.bar-count {
  position: absolute;
  bottom: 100%;
  font-size: 0.625rem;
  color: var(--text-secondary);
  padding-bottom: 2px;
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
