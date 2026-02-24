<template>
  <div class="boundary-view">
    <div class="card">
      <div class="flex items-center justify-between mb-md">
        <div>
          <h2>Draw Field Boundary</h2>
          <p class="text-muted">
            Draw or adjust the boundary for your field. The boundary defines 
            the area where zones will be generated.
          </p>
        </div>
        <div class="flex gap-sm">
          <button class="btn btn-secondary" @click="clearDrawing">
            Clear
          </button>
          <button class="btn btn-primary" @click="useDefaultBoundary">
            Use Default
          </button>
        </div>
      </div>
      
      <!-- Drawing Tools -->
      <div class="toolbar mb-md">
        <button 
          class="tool-btn"
          :class="{ active: drawMode === 'polygon' }"
          @click="drawMode = 'polygon'"
        >
          <span class="tool-icon">⬡</span>
          Draw Polygon
        </button>
        <button 
          class="tool-btn"
          :class="{ active: drawMode === 'modify' }"
          @click="drawMode = 'modify'"
        >
          <span class="tool-icon">✎</span>
          Modify
        </button>
        <button 
          class="tool-btn"
          :class="{ active: drawMode === 'delete' }"
          @click="drawMode = 'delete'"
        >
          <span class="tool-icon">✕</span>
          Delete Point
        </button>
      </div>
      
      <!-- Map -->
      <div ref="mapContainer" class="map-container"></div>
      
      <!-- Info Panel -->
      <div class="info-panel mt-md">
        <div class="grid grid-3">
          <div class="info-item">
            <span class="info-label">Field Type</span>
            <span class="info-value">{{ fieldTypeLabel }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Points</span>
            <span class="info-value">{{ pointCount }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Area</span>
            <span class="info-value">{{ area }}</span>
          </div>
        </div>
      </div>
      
      <!-- Actions -->
      <div class="flex justify-between mt-lg">
        <button class="btn btn-secondary btn-large" @click="goBack">
          ← Back
        </button>
        <button class="btn btn-success btn-large" @click="continueToZones">
          Generate Zones →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useZoneStore } from '../stores/zoneStore'
import Map from 'ol/Map'
import View from 'ol/View'
import { Draw, Modify, Select } from 'ol/interaction'
import { Polygon, LineString } from 'ol/geom'
import VectorSource from 'ol/source/Vector.js'
import VectorLayer from 'ol/layer/Vector.js'
import { GeoJSON } from 'ol/format'
import { bbox as bboxStrategy } from 'ol/loadingstrategy'
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'

const router = useRouter()
const store = useZoneStore()

const mapContainer = ref(null)
const drawMode = ref('polygon')
let map = null
let drawInteraction = null
let modifyInteraction = null
let boundaryLayer = null
let boundarySource = null

const fieldTypeLabel = computed(() => {
  const types = { 1: 'Rectangular', 2: 'Center Pivot VRI', 3: 'Irregular' }
  return types[store.fieldType] || 'Unknown'
})

const pointCount = computed(() => {
  if (!boundarySource) return 0
  const features = boundarySource.getFeatures()
  if (!features.length) return 0
  const geom = features[0].getGeometry()
  return geom.getCoordinates()[0]?.length || 0
})

const area = computed(() => {
  if (!boundarySource) return '0 m²'
  const features = boundarySource.getFeatures()
  if (!features.length) return '0 m²'
  const geom = features[0].getGeometry()
  const area = geom.getArea()
  if (area > 1000000) {
    return `${(area / 1000000).toFixed(2)} km²`
  }
  return `${area.toFixed(0)} m²`
})

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map) {
    map.setTarget(null)
  }
})

watch(drawMode, (mode) => {
  updateInteractions()
})

function initMap() {
  // Create vector source for boundary
  boundarySource = new VectorSource()
  
  boundaryLayer = new VectorLayer({
    source: boundarySource,
    style: {
      'fill-color': 'rgba(29, 155, 240, 0.2)',
      'stroke-color': '#1d9bf0',
      'stroke-width': 2
    }
  })
  
  // Create map
  map = new Map({
    target: mapContainer.value,
    layers: [
      new TileLayer({
        source: new OSM()
      }),
      boundaryLayer
    ],
    view: new View({
      center: [0, 0],
      zoom: 2
    })
  })
  
  // If we have a boundary from session, load it
  if (store.boundary) {
    loadBoundary(store.boundary)
  }
  
  updateInteractions()
}

function updateInteractions() {
  // Remove existing interactions
  if (drawInteraction) {
    map.removeInteraction(drawInteraction)
    drawInteraction = null
  }
  if (modifyInteraction) {
    map.removeInteraction(modifyInteraction)
    modifyInteraction = null
  }
  
  if (drawMode.value === 'polygon') {
    drawInteraction = new Draw({
      source: boundarySource,
      type: 'Polygon'
    })
    map.addInteraction(drawInteraction)
    
    drawInteraction.on('drawend', (e) => {
      // Convert to GeoJSON and store
      const geojson = new GeoJSON().writeFeatureObject(e.feature)
      store.setBoundary(geojson)
    })
  } else if (drawMode.value === 'modify') {
    modifyInteraction = new Modify({
      source: boundarySource
    })
    map.addInteraction(modifyInteraction)
    
    modifyInteraction.on('modifyend', () => {
      const features = boundarySource.getFeatures()
      if (features.length) {
        const geojson = new GeoJSON().writeFeatureObject(features[0])
        store.setBoundary(geojson)
      }
    })
  }
}

function loadBoundary(geojson) {
  boundarySource.clear()
  const feature = new GeoJSON().readFeature(geojson)
  boundarySource.addFeature(feature)
  
  // Fit view to boundary
  const geom = feature.getGeometry()
  map.getView().fit(geom, { padding: [50, 50, 50, 50] })
}

function clearDrawing() {
  boundarySource.clear()
  store.setBoundary(null)
}

function useDefaultBoundary() {
  if (store.boundary) {
    loadBoundary(store.boundary)
  }
}

function goBack() {
  router.push('/')
}

async function continueToZones() {
  if (!store.boundary) {
    store.error = 'Please draw a boundary first'
    return
  }
  
  try {
    await store.generateZones(10)
    router.push('/zones')
  } catch (e) {
    // Error handled in store
  }
}
</script>

<style scoped>
.boundary-view {
  max-width: 1200px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  gap: var(--space-sm);
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tool-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.tool-btn.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.tool-icon {
  font-size: 1rem;
}

.info-panel {
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: var(--space-md);
}

.info-item {
  text-align: center;
}

.info-label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-value {
  display: block;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-top: var(--space-xs);
}
</style>
