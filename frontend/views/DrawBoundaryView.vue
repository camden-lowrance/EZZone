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
          Delete
        </button>
      </div>
      
      <!-- Map -->
      <div ref="mapContainer" class="map-container"></div>
      
      <!-- Info Panel -->
      <div class="info-panel mt-md">
        <div class="grid grid-2">
          <div class="info-item">
            <span class="info-label">Detected CRS</span>
            <span class="info-value">{{ store.results.detectedCrs || 'Auto' }}</span>
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
import { useZoneStore } from '../stores/zoneStore'
import Map from 'ol/Map'
import View from 'ol/View'
import { Draw, Modify, Snap } from 'ol/interaction'
import VectorSource from 'ol/source/Vector.js'
import VectorLayer from 'ol/layer/Vector.js'
import { GeoJSON } from 'ol/format'
import { Circle, Fill, Stroke, Style } from 'ol/style'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'
import { getArea as getSphereArea } from 'ol/sphere'

const store = useZoneStore()

const mapContainer = ref(null)
const drawMode = ref('modify')
let map = null
let currentInteraction = null
let snapInteraction = null
let boundaryLayer = null
let boundarySource = null

const _useAcres = new Intl.Locale(navigator.language).region === 'US'
const areaM2 = ref(0)

const area = computed(() => {
  if (areaM2.value <= 0) return _useAcres ? '0 ac' : '0 ha'
  if (_useAcres) return `${(areaM2.value / 4046.856).toFixed(1)} ac`
  return `${(areaM2.value / 10000).toFixed(2)} ha`
})

function updateArea() {
  if (!boundarySource) { areaM2.value = 0; return }
  const features = boundarySource.getFeatures()
  if (!features.length) { areaM2.value = 0; return }
  areaM2.value = getSphereArea(features[0].getGeometry(), { projection: 'EPSG:3857' })
}

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

const boundaryStyle = new Style({
  fill: new Fill({ color: 'rgba(29, 155, 240, 0.2)' }),
  stroke: new Stroke({ color: '#1d9bf0', width: 2 }),
  image: new Circle({
    radius: 5,
    fill: new Fill({ color: '#1d9bf0' }),
    stroke: new Stroke({ color: '#fff', width: 2 })
  })
})

const geojsonFormat = new GeoJSON({
  dataProjection: 'EPSG:4326',
  featureProjection: 'EPSG:3857'
})

function initMap() {
  boundarySource = new VectorSource()

  boundaryLayer = new VectorLayer({
    source: boundarySource,
    style: boundaryStyle
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
      boundaryLayer
    ],
    view: new View({
      center: [0, 0],
      zoom: 2
    })
  })

  if (store.results.boundary) {
    loadBoundary(store.results.boundary)
  }

  updateInteractions()
}

function removeInteractions() {
  if (currentInteraction) {
    map.removeInteraction(currentInteraction)
    currentInteraction = null
  }
  if (snapInteraction) {
    map.removeInteraction(snapInteraction)
    snapInteraction = null
  }
  map.un('singleclick', handleDeleteClick)
}

function syncBoundary() {
  const features = boundarySource.getFeatures()
  if (features.length) {
    store.results.boundary = geojsonFormat.writeFeatureObject(features[0])
  }
}

function updateInteractions() {
  removeInteractions()

  if (drawMode.value === 'polygon') {
    currentInteraction = new Draw({
      source: boundarySource,
      type: 'Polygon'
    })
    map.addInteraction(currentInteraction)
    currentInteraction.on('drawend', (e) => {
      // Clear previous boundary before adding new one
      boundarySource.clear()
      setTimeout(() => { syncBoundary(); updateArea() }, 0)
    })
  } else if (drawMode.value === 'modify') {
    // Modify lets you drag vertices; Alt+click on a vertex deletes it
    currentInteraction = new Modify({
      source: boundarySource
    })
    map.addInteraction(currentInteraction)
    currentInteraction.on('modifyend', () => { syncBoundary(); updateArea() })
  } else if (drawMode.value === 'delete') {
    // Click a feature to remove it entirely
    map.on('singleclick', handleDeleteClick)
  }

  // Snap to existing vertices in all modes
  snapInteraction = new Snap({ source: boundarySource })
  map.addInteraction(snapInteraction)
}

function handleDeleteClick(e) {
  if (drawMode.value !== 'delete') return
  map.forEachFeatureAtPixel(e.pixel, (feature) => {
    boundarySource.removeFeature(feature)
    store.results.boundary = null
    return true // stop after first hit
  })
}

function loadBoundary(geojson) {
  boundarySource.clear()
  const feature = geojsonFormat.readFeature(geojson)
  boundarySource.addFeature(feature)
  
  // Fit view to boundary
  const geom = feature.getGeometry()
  map.getView().fit(geom, { padding: [50, 50, 50, 50] })
  updateArea()
}

function clearDrawing() {
  boundarySource.clear()
  store.results.boundary = null
  updateArea()
}

function useDefaultBoundary() {
  if (store.results.boundary) {
    loadBoundary(store.results.boundary)
  }
}

function goBack() {
  store.step = 1
}

async function continueToZones() {
  if (!store.results.boundary) {
    store.error = 'Please draw a boundary first'
    return
  }
  
  try {
    await store.generateZones()
    store.step = 3
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
