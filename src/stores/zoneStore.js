import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useZoneStore = defineStore('zones', () => {
  // State
  const sessionId = ref(null)
  const dataPoints = ref({ x: [], y: [], z: [] })
  const boundary = ref(null)
  const fieldType = ref(1) // 1=rect, 2=VRI, 3=irreg
  const epsg = ref('4326')
  const units = ref('m')
  const rowSpacing = ref(100)
  const pivotSpacing = ref(50)
  const pivotLength = ref(500)
  
  // Zone generation results
  const zones = ref(null)
  const gvf = ref([])
  const classBreaks = ref([])
  const legend = ref(null)
  const gridStats = ref(null)
  
  // UI state
  const loading = ref(false)
  const error = ref(null)
  const step = ref(1) // 1=data, 2=boundary, 3=zones, 4=finalize
  
  // Computed
  const hasData = computed(() => dataPoints.value.x.length > 0)
  const hasBoundary = computed(() => boundary.value !== null)
  const hasZones = computed(() => zones.value !== null)
  
  // Actions
  async function initSession(file, columns) {
    loading.value = true
    error.value = null
    
    try {
      const formData = new FormData()
      if (file) {
        formData.append('file', file)
      }
      formData.append('columns', JSON.stringify(columns))
      formData.append('epsg', epsg.value)
      formData.append('field_type', fieldType.value)
      formData.append('units', units.value)
      formData.append('row_spacing', rowSpacing.value)
      formData.append('pivot_spacing', pivotSpacing.value)
      formData.append('pivot_length', pivotLength.value)
      
      const response = await fetch('/api/session/init', {
        method: 'POST',
        body: formData
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to initialize session')
      }
      
      const data = await response.json()
      sessionId.value = data.session_id
      boundary.value = data.boundary
      gridStats.value = data.grid_stats
      
      step.value = 2
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  async function generateZones(numClasses = 10) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch('/api/zones/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          boundary_geojson: boundary.value,
          num_classes: numClasses
        })
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to generate zones')
      }
      
      const data = await response.json()
      gvf.value = data.gvf
      classBreaks.value = data.class_breaks
      
      step.value = 3
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  async function finalizeZones(numClasses) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch('/api/zones/finalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ num_classes: numClasses })
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to finalize zones')
      }
      
      const data = await response.json()
      zones.value = data.zones
      classBreaks.value = data.class_breaks
      legend.value = data.legend
      
      step.value = 4
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  async function simplifyZones(smooth) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch('/api/zones/simplify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ smooth })
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to simplify zones')
      }
      
      const data = await response.json()
      zones.value = data.zones
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  async function exportZones(format) {
    try {
      const response = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format })
      })
      
      if (!response.ok) {
        throw new Error('Failed to export zones')
      }
      
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = format === 'geojson' ? 'zones.geojson' : 'zones.zip'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      error.value = e.message
      throw e
    }
  }
  
  function setBoundary(geojson) {
    boundary.value = geojson
  }
  
  function reset() {
    sessionId.value = null
    dataPoints.value = { x: [], y: [], z: [] }
    boundary.value = null
    zones.value = null
    gvf.value = []
    classBreaks.value = []
    legend.value = null
    gridStats.value = null
    loading.value = false
    error.value = null
    step.value = 1
  }
  
  return {
    // State
    sessionId,
    dataPoints,
    boundary,
    fieldType,
    epsg,
    units,
    rowSpacing,
    pivotSpacing,
    pivotLength,
    zones,
    gvf,
    classBreaks,
    legend,
    gridStats,
    loading,
    error,
    step,
    
    // Computed
    hasData,
    hasBoundary,
    hasZones,
    
    // Actions
    initSession,
    generateZones,
    finalizeZones,
    simplifyZones,
    exportZones,
    setBoundary,
    reset
  }
})
