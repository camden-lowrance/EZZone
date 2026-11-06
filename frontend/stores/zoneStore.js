import { defineStore } from 'pinia'
import { ref } from 'vue'
import { STEPS } from '../steps.js'

export const useZoneStore = defineStore('zones', () => {
  const step = ref(STEPS.UPLOAD)
  const loading = ref(false)
  const error = ref(null)
  const dataId = ref(null)
  
  const config = ref({
    numClasses: 3
  })

  // Metadata set by HomeView after a successful initSession, consumed by DataView
  const uploadMeta = ref({
    fileLabel: 'Sample Data',
    rawFiles: [],
    initialZ: '',
    initialCrs: '',
    isSampleMode: false,
  })
  
  const results = ref({
    detectedCrs: null,
    isCrsGuessed: false,
    detectedZ: null,
    allColumns: [],
    numericColumns: [],
    previewData: [],
    boundary: null,
    zones: null,
    gvf: [],
    classBreaks: [],
    legend: null,
    numPoints: 0,
    originalNumPoints: 0,
    pointsUsed: 0
  })

  async function initSession(files, zColumn = '', crs = '', useSample = false) {
    loading.value = true; error.value = null
    try {
      const formData = new FormData()
      if (Array.isArray(files) && files.length) {
        files.forEach(f => formData.append('file', f))
      }
      if (useSample) formData.append('use_sample', '1')
      if (zColumn) formData.append('z_column', zColumn)
      if (crs) formData.append('crs', crs)
      
      const res = await fetch('/api/session/init', { method: 'POST', body: formData })
      if (!res.ok) {
        const body = await res.json()
        throw new Error(body.error || 'An unexpected error occurred. Please try again.')
      }
      
      const data = await res.json()
      dataId.value = data.data_id
      results.value.boundary = data.boundary
      results.value.numPoints = data.num_points
      results.value.originalNumPoints = data.original_num_points ?? data.num_points
      results.value.pointsUsed = data.points_used ?? data.num_points
      results.value.detectedCrs = data.detected_crs
      results.value.isCrsGuessed = data.is_crs_guessed || false
      results.value.detectedZ = data.detected_z
      results.value.allColumns = data.all_columns || []
      results.value.numericColumns = data.numeric_columns || []
      results.value.previewData = data.preview_data || []
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
      step.value = STEPS.ZONES
    } catch (e) { error.value = e.message } finally { loading.value = false }
  }

  async function finalizeZones() {
    await generateZones()
    step.value = STEPS.FINALIZE
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
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) { error.value = e.message }
  }
  
  function reset() {
    dataId.value = null
    results.value = {
      detectedCrs: null,
      isCrsGuessed: false,
      detectedZ: null,
      allColumns: [],
      numericColumns: [],
      previewData: [],
      boundary: null,
      zones: null,
      gvf: [],
      classBreaks: [],
      legend: null,
      numPoints: 0,
      originalNumPoints: 0,
      pointsUsed: 0
    }
    step.value = STEPS.UPLOAD
    error.value = null
    uploadMeta.value = { fileLabel: 'Sample Data', rawFiles: [], initialZ: '', initialCrs: '', isSampleMode: false }
  }
  
  return {
    step, loading, error, config, results, uploadMeta,
    initSession, generateZones, finalizeZones, exportZones, reset
  }
})
