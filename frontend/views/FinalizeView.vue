<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="grid grid-cols-2 gap-4">
      <!-- Map & Export -->
      <div class="card">
        <h2>Final Zones</h2>
        <p class="text-muted mb-4">
          Your zones are ready. Export them for use in your precision
          agriculture systems.
        </p>

        <div ref="mapContainer" class="map-container mb-4"></div>

        <div class="bg-bg-tertiary rounded p-4 mt-6">
          <h4 class="mb-4">Export Zones</h4>
          <div class="flex gap-4">
            <button class="btn btn-secondary btn-large flex items-center gap-2" @click="exportGeoJSON">
              <IconGeoJSON :size="20" /> Download GeoJSON
            </button>
            <button class="btn btn-secondary btn-large flex items-center gap-2" @click="exportShapefile">
              <IconShapefile :size="20" /> Download Shapefile
            </button>
          </div>
        </div>

        <div class="flex justify-between mt-6">
          <button class="btn btn-secondary" @click="goBack">← Back to Zones</button>
          <button class="btn btn-primary" @click="startOver">Start Over</button>
        </div>
      </div>

      <!-- Summary -->
      <div class="card">
        <h2>Summary</h2>

        <div class="grid grid-cols-2 gap-4 mt-4">
          <div class="bg-bg-tertiary rounded p-4 text-center">
            <span class="meta-label">Source CRS</span>
            <span class="stat-value" style="font-size: 1rem">{{ store.results.detectedCrs }}</span>
          </div>
          <div class="bg-bg-tertiary rounded p-4 text-center">
            <span class="meta-label">Source Column</span>
            <span class="stat-value">{{ store.results.detectedZ }}</span>
          </div>
          <div class="bg-bg-tertiary rounded p-4 text-center">
            <span class="meta-label">Classes</span>
            <span class="stat-value">{{ numClasses }}</span>
          </div>
          <div class="bg-bg-tertiary rounded p-4 text-center">
            <span class="meta-label">GVF Score</span>
            <span class="stat-value">{{ gvfScore }}</span>
          </div>
        </div>

        <!-- Class Distribution -->
        <div class="mt-6">
          <h4>Class Distribution</h4>
          <div class="mt-2" style="height: 280px; width: 100%;">
            <Doughnut v-if="pieData" :data="pieData" :options="pieOptions" />
          </div>
        </div>

        <!-- Legend -->
        <div v-if="store.results.legend" class="mt-6">
          <h4>Legend</h4>
          <div class="legend-items mt-2">
            <div v-for="(item, i) in store.results.legend" :key="i" class="legend-item">
              <span class="legend-color" :style="{ background: item[0] }"></span>
              <span class="legend-label">{{ item[1] }}</span>
            </div>
          </div>
        </div>

        <div class="alert alert-success mt-6">
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
import { STEPS } from '../steps.js'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import IconGeoJSON from '../components/IconGeoJSON.vue'
import IconShapefile from '../components/IconShapefile.vue'
import Map from 'ol/Map'
import View from 'ol/View'
import VectorSource from 'ol/source/Vector.js'
import VectorLayer from 'ol/layer/Vector.js'
import { GeoJSON } from 'ol/format'
import { Fill, Stroke, Style } from 'ol/style'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'

ChartJS.register(ArcElement, Tooltip, Legend)

const store = useZoneStore()

const mapContainer = ref(null)
let map = null
let zonesLayer = null
let zonesSource = null

const numClasses = computed(() => store.results.legend?.length || 0)

const gvfScore = computed(() => {
  if (!store.results.gvf?.length) return 'N/A'
  const last = store.results.gvf[store.results.gvf.length - 1]
  return last ? last[1].toFixed(3) : 'N/A'
})

const classDistribution = computed(() => {
  if (!store.results.zones?.features) return []
  const counts = {}
  store.results.zones.features.forEach(f => {
    const cls = f.properties?.zone || 1
    counts[cls] = (counts[cls] || 0) + 1
  })
  return Array.from({ length: numClasses.value }, (_, i) => counts[i + 1] || 0)
})

const pieData = computed(() => {
  if (!classDistribution.value.length) return null
  const colors = classDistribution.value.map((_, i) =>
    (store.results.legend && store.results.legend[i]) ? store.results.legend[i][0] : '#1d9bf0'
  )
  return {
    labels: classDistribution.value.map((_, i) => `Zone ${i + 1}`),
    datasets: [{
      data: classDistribution.value,
      backgroundColor: colors,
      borderColor: colors.map(c => c + 'cc'),
      borderWidth: 1,
    }]
  }
})

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  layout: { padding: { right: 40 } },
  plugins: {
    legend: {
      position: 'right',
      labels: {
        color: '#8ba0b8',
        font: { size: 15 },
        padding: 10,
        boxWidth: 12,
        boxHeight: 12,
      }
    },
    tooltip: {
      callbacks: {
        label: (ctx) => ` ${ctx.label}: ${ctx.parsed}`
      }
    }
  }
}

onMounted(() => { initMap() })
onUnmounted(() => { if (map) map.setTarget(null) })
watch(toRef(store.results, 'zones'), () => { if (map) loadZones() })

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
    view: new View({ center: [0, 0], zoom: 2 })
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
  map.getView().fit(zonesSource.getExtent(), { padding: [50, 50, 50, 50] })
}

async function exportGeoJSON() { await store.exportZones('geojson') }
async function exportShapefile() { await store.exportZones('shapefile') }
function goBack() { store.step = STEPS.ZONES }
function startOver() { store.reset() }
</script>

<style scoped>
.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 0.25rem;
}
</style>
