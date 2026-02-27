<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="grid grid-cols-2 gap-4">
      <!-- Map & Controls -->
      <div class="card">
        <h2>Generated Zones</h2>
        <p class="text-muted mb-4">
          View the generated zones. Adjust the number of classes to find
          the optimal grouping.
        </p>

        <div ref="mapContainer" class="map-container mb-4"></div>

        <!-- Class Selection -->
        <div class="form-group">
          <label class="form-label">
            Number of Classes: {{ store.config.numClasses }}
          </label>
          <input
            v-model.number="store.config.numClasses"
            type="range"
            class="slider"
            min="2"
            max="8"
            @change="regenerateZones"
          />
          <div class="range-labels">
            <span>2</span>
            <span>8</span>
          </div>
        </div>

        <!-- Legend -->
        <div v-if="store.results.legend" class="mt-4">
          <h4 class="mb-2">Legend</h4>
          <div class="legend-items">
            <div v-for="(item, i) in store.results.legend" :key="i" class="legend-item">
              <span class="legend-color" :style="{ background: item[0] }"></span>
              <span class="legend-label">{{ item[1] }}</span>
            </div>
          </div>
        </div>

        <div class="flex justify-between mt-6">
          <button class="btn btn-secondary" @click="goBack">← Back</button>
          <button class="btn btn-success" @click="continueToFinalize">Finalize Zones →</button>
        </div>
      </div>

      <!-- GVF Chart -->
      <div class="card">
        <h2>Goodness of Variance Fit (GVF)</h2>
        <p class="text-muted mb-4">
          The GVF chart shows how well the zones group your data.
          Higher values indicate better grouping.
        </p>

        <div class="h-[300px]">
          <Line :data="chartData" :options="chartOptions" />
        </div>

        <div class="mt-6">
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

        <div class="alert alert-info mt-6">
          <strong>Tip:</strong> The optimal number of classes is typically where
          the GVF curve starts to flatten out (the "elbow").
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, toRef } from 'vue'
import { useZoneStore } from '../stores/zoneStore'
import { STEPS } from '../steps.js'
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
import { Fill, Stroke, Style } from 'ol/style'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

const store = useZoneStore()

const mapContainer = ref(null)
let map = null
let zonesLayer = null
let zonesSource = null

const chartData = computed(() => {
  const labels = store.results.gvf.map((_, i) => i + 2)
  const gvfValues = store.results.gvf.map(g => g[1])
  const currentClasses = store.config.numClasses

  return {
    labels,
    datasets: [{
      label: 'GVF Score',
      data: gvfValues,
      borderColor: '#00ff88',
      backgroundColor: 'rgba(0, 255, 136, 0.1)',
      borderWidth: 3,
      pointBackgroundColor: labels.map(l => l === currentClasses ? '#00ff88' : '#1c1e20'),
      pointBorderColor: labels.map(l => l === currentClasses ? '#ffffff' : '#00ff88'),
      pointRadius: labels.map(l => l === currentClasses ? 8 : 4),
      pointHoverRadius: 10,
      fill: true,
      tension: 0.4
    }]
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1c1e20',
      titleColor: '#00f3ff',
      bodyColor: '#ffffff',
      borderColor: '#38444d',
      borderWidth: 1,
      displayColors: false,
      callbacks: { label: (ctx) => `GVF Score: ${ctx.parsed.y.toFixed(3)}` }
    }
  },
  scales: {
    x: {
      title: { display: true, text: 'Number of Classes', color: '#8b98a5', font: { size: 14, weight: 'bold' } },
      grid: { color: 'rgba(56, 68, 77, 0.3)' },
      ticks: { color: '#8b98a5', font: { size: 13 } }
    },
    y: {
      title: { display: true, text: 'Grouping Quality (GVF)', color: '#8b98a5', font: { size: 14, weight: 'bold' } },
      grid: { color: 'rgba(56, 68, 77, 0.3)' },
      ticks: { color: '#8b98a5', font: { size: 13 }, callback: (v) => (v * 100).toFixed(0) + '%' },
      min: 0,
      max: 1.05
    }
  }
}))

const classBreakTable = computed(() => store.results.classBreaks)

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

async function regenerateZones() {
  try { await store.generateZones(); loadZones() } catch (e) { /* handled in store */ }
}

function goBack() { store.step = STEPS.BOUNDARY }

async function continueToFinalize() {
  try { await store.finalizeZones() } catch (e) { /* handled in store */ }
}
</script>
