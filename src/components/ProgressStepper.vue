<template>
  <div class="stepper">
    <div 
      v-for="(s, i) in steps" 
      :key="i"
      class="step"
      :class="{ 
        active: currentStep === i + 1, 
        completed: currentStep > i + 1 
      }"
    >
      <div class="step-indicator">
        <span v-if="currentStep > i + 1">✓</span>
        <span v-else>{{ i + 1 }}</span>
      </div>
      <span class="step-label">{{ s }}</span>
      <div v-if="i < steps.length - 1" class="step-connector"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  currentStep: {
    type: Number,
    required: true
  }
})

const steps = ['Upload Data', 'Draw Boundary', 'Generate Zones', 'Finalize']
</script>

<style scoped>
.stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: var(--space-xl);
  padding: var(--space-md) 0;
}

.step {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  position: relative;
}

.step-indicator {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-muted);
  transition: all var(--transition-normal);
}

.step.active .step-indicator {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.step.completed .step-indicator {
  background: var(--accent-green);
  border-color: var(--accent-green);
  color: white;
}

.step-label {
  font-size: 0.875rem;
  color: var(--text-muted);
  font-weight: 500;
}

.step.active .step-label {
  color: var(--text-primary);
}

.step.completed .step-label {
  color: var(--text-secondary);
}

.step-connector {
  width: 60px;
  height: 2px;
  background: var(--border-color);
  margin: 0 var(--space-sm);
}

.step.completed .step-connector {
  background: var(--accent-green);
}

@media (max-width: 768px) {
  .stepper {
    flex-wrap: wrap;
    gap: var(--space-sm);
  }
  
  .step-connector {
    display: none;
  }
  
  .step-label {
    display: none;
  }
}
</style>
