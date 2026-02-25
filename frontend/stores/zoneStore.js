import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useZoneStore = defineStore('zones', () => {
  const step = ref(1)
  const loading = ref(false)
  const error = ref(null)
  const dataId = ref(null)
  
  const config = ref({
    numClasses: 3,
    zColumn: '' // User can specify which column has the values
  })
  
  const results = ref({
    detectedCrs: null,
    detectedZ: null,
    boundary: null,
    zones: null,
    gvf: [],
    classBreaks: [],
    legend: null,
    gridStats: null
  })

  async function initSession(file, zColumn = '') {
    loading.value = true; error.value = null
    try {
      const formData = new FormData()
      if (file) formData.append('file', file)
      if (zColumn) formData.append('z_column', zColumn)
      
      const res = await fetch('/api/session/init', { method: 'POST', body: formData })
      if (!res.ok) throw new Error((await res.json()).error)
      
      const data = await res.json()
      dataId.value = data.data_id
      results.value.boundary = data.boundary
      results.value.gridStats = data.grid_stats
      results.value.detectedCrs = data.detected_crs
      results.value.detectedZ = data.detected_z
      step.value = 2
    } catch (e) { error.value = e.message } finally { loading.value = false }
  }
  
  async function generateZones() {
    loading.value = true; error.value = null
    try {
      const res = await fetch('/api/zones/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data_id: dataId.value,
          boundary_geojson: results.value.boundary,
          num_classes: config.value.numClasses
        })
      })
      if (!res.ok) throw new Error((await res.json()).error)
      
      const data = await res.json()
      results.value.zones = data.zones
      results.value.gvf = data.gvf
      results.value.classBreaks = data.class_breaks
      results.value.legend = data.legend
      step.value = 3
    } catch (e) { error.value = e.message } finally { loading.value = false }
  }
  
  async function finalizeZones() {
    await generateZones()
    step.value = 4
  }
  
  async function exportZones(format) {
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_id: dataId.value, format })
      })
      if (!res.ok) throw new Error('Export failed')
      
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `zones.${format === 'geojson' ? 'geojson' : 'zip'}`
      a.click()
    } catch (e) { error.value = e.message }
  }
  
  function reset() {
    dataId.value = null
    results.value = { detectedCrs: null, detectedZ: null, boundary: null, zones: null, gvf: [], classBreaks: [], legend: null, gridStats: null }
    step.value = 1
    error.value = null
  }
  
  return {
    step, loading, error, config, results,
    initSession, generateZones, finalizeZones, exportZones, reset
  }
})
